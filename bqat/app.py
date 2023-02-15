import datetime
import glob
import json
import os
import shutil
import time
import warnings
from zipfile import ZipFile

import click
import psutil
import ray
from .core.bqat_core import scan
from .core.bqat_core.utils import extend
from cpuinfo import get_cpu_info
from rich.console import Console
from rich.progress import MofNCompleteColumn, Progress, SpinnerColumn

from bqat import __version__ as version
from bqat.utils import convert_ram, validate_path, write_csv, write_log, write_report, filter_output


def run(
    mode: str,
    input_folder: str,
    output_folder: str,
    # report_dir: str,
    # log_dir: str,
    limit: int,
    pattern: str,
    single: bool,
    type: list,
    convert: list,
    target: str,
    attributes: str,
    query: str,
    sort: str,
    cwd: str
) -> None:

    warnings.simplefilter(action="ignore", category=FutureWarning)
    warnings.simplefilter(action="ignore", category=RuntimeWarning)
    warnings.simplefilter(action="ignore", category=UserWarning)

    TYPE = type

    print("> Analyse:")
    click.echo(f"Mode: {mode.upper()}")
    job_timer = time.time()

    if not os.path.exists(input_folder):
        click.echo(
            f"Input directory not found. Make sure your local `data/` folder mounted.\n"
        )
        return
    else:
        input_folder = validate_path(input_folder)

    file_total = 0
    for ext in extend(TYPE):
        file_total += len(
            glob.glob(input_folder + f"**/{pattern}." + ext, recursive=True)
        )
    click.echo(f"Input: {input_folder} ({file_total} samples)\n")

    if limit:
        click.echo(f"Scan number limit: {limit}")
        if limit < file_total:
            file_total = limit

    if file_total == 0:
        click.echo(f"Exit. No valid input file.\n")
        return

    # if log_dir.rfind(".") == -1:
    #     log_dir = validate_path(log_dir)
    #     log_dir += "log.json"
    # if report_dir.rfind(".") == -1:
    #     report_dir = validate_path(report_dir)
    #     report_dir += "report.html"

    dt = datetime.datetime.today()
    timestamp = f"{dt.day}-{dt.month}-{dt.year}_{dt.hour}-{dt.minute}-{dt.second}"
    output_folder = validate_path(output_folder)
    output_dir = output_folder + f"output_{mode}_{timestamp}.csv"
    log_dir = output_folder + f"log_{mode}_{timestamp}.json"
    report_dir = output_folder + f"report_{mode}_{timestamp}.html"

    write_log(log_dir, init=True)

    file_globs = []
    for ext in extend(TYPE):
        file_globs.append(
            glob.iglob(input_folder + f"**/{pattern}." + ext, recursive=True)
        )

    file_count = 0
    tasks = []

    write_csv(output_dir, init=True)

    if single:
        with Progress(
            SpinnerColumn(), MofNCompleteColumn(), *Progress.get_default_columns()
        ) as p:
            task_progress = p.add_task("[purple]Scanning...", total=file_total)
            for files in file_globs:
                for path in files:
                    result = scan(path, mode=mode, source=convert, target=target)

                    log = result.get("log", {})
                    if log:
                        log.update({"file": path})
                        write_log(log_dir, log)
                    header = False if "error" in list(log.keys()) else True

                    if result:
                        write_csv(output_dir, result, header)

                    file_count += 1
                    p.update(task_progress, advance=1)
                    if p.finished:
                        break
                if p.finished:
                    break

    else:
        with Progress(
            SpinnerColumn(), MofNCompleteColumn(), *Progress.get_default_columns()
        ) as p:
            task_progress = p.add_task("[cyan]Sending task...", total=file_total)
            for files in file_globs:
                for path in files:
                    tasks.append(
                        scan_task.remote(
                            path, output_dir, log_dir, mode, convert, target
                        )
                    )
                    file_count += 1
                    p.update(task_progress, advance=1)
                    if p.finished:
                        break
                if p.finished:
                    break

                # # Load limiter
                # if len(tasks) > 1000:
                #     ready = len(tasks) - 1000
                #     ray.wait(tasks, num_returns=ready)

        eta_step = 10  # ETA estimation interval
        ready, not_ready = ray.wait(tasks)

        with Progress(
            SpinnerColumn(), MofNCompleteColumn(), *Progress.get_default_columns()
        ) as p:
            task_progress = p.add_task("[cyan]Scanning...", total=file_total)
            while not p.finished:
                if len(not_ready) < eta_step:
                    p.update(task_progress, completed=file_total)
                    continue
                tasks = not_ready
                ready, not_ready = ray.wait(tasks, num_returns=eta_step)
                p.update(task_progress, advance=len(ready))

        ray.get(not_ready)

    write_log(log_dir, finish=True)
    job_timer = time.time() - job_timer
    sc = job_timer
    mn, sc = divmod(sc, 60)
    hr, mn = divmod(mn, 60)
    sc, mn, hr = int(sc), int(mn), int(hr)

    try:
        log_out = {
            "metadata": {
                "version": "BQAT v" + version,
                "datetime": str(dt),
                "input directory": input_folder,
                "processed": file_count,
                "log": None,
                "process time": f"{hr}h{mn}m{sc}s",
            }
        }
        with open(log_dir, "r") as f:
            logs = json.load(f)
            log_out["metadata"].update({"log": len(logs)})
            log_out["log"] = logs
        with open(log_dir, "w") as f:
            json.dump(log_out, f)
    except Exception as e:
        click.echo(f"failed to reload metadata for log: {str(e)}")

    try:
        write_report(
            report_dir,
            output_dir,
            f"Biometric Quality Report (BQAT v{version})"
        )
    except Exception as e:
        click.echo(f"failed to generate report: {str(e)}")

    try:
        dir = filter_output(
            output_dir,
            attributes,
            query,
            sort,
            cwd
        )
        outlier_filter = {
            "Output": dir.get("output"),
            "Report": dir.get("report")
        } if dir else False
    except Exception as e:
        click.echo(f"failed to apply filter: {str(e)}")

    print("\n> Summary:")
    summary = {
        "Total process time": f"{hr}h{mn}m{sc}s",
        "System throughput": f"{file_count/job_timer:.2f} item/s",
        "Assessment Task": {
            "File processed": file_count,
            "Input": f"{input_folder}",
            "Output": f"{os.path.relpath(output_dir, os.getcwd())}",
            "Report": f"{report_dir}",
            "Log": f"{log_dir}",
        }
    }
    if outlier_filter:
        summary.update({"Outlier Filter": outlier_filter})
    Console().print_json(json.dumps(summary))
    print("\n>> Finished <<\n")


def filter(output, attributes, query, sort, cwd):
    try:
        dir = filter_output(
            output,
            attributes,
            query,
            sort,
            cwd
        )
        outlier_filter = {
            "Output": dir.get("output"),
            "Report": dir.get("report")
        } if dir else False
    except Exception as e:
        click.echo(f"failed to apply filter: {str(e)}")
    print("\n> Summary:")
    summary = {"Outlier Filter": outlier_filter}
    Console().print_json(json.dumps(summary))
    print("\n>> Finished <<\n")


def benchmark(mode: str, limit: int, single: bool) -> None:
    """Run benchmark to profile the capability of host system."""
    click.echo(f">> Start Benchmark <<\n")
    click.echo(f"Mode: {mode.upper()}")

    TYPE = ["wsq", "jpg", "jpeg", "png", "bmp", "jp2"]

    if mode == "fingerprint" or mode == "finger":
        samples = f"samples/fingerprint.zip"
    elif mode == "face":
        samples = f"samples/face.zip"
    elif mode == "iris":
        samples = f"samples/iris.zip"
    else:
        raise RuntimeError(f"{mode} not support")

    with ZipFile(samples, "r") as z:
        z.extractall(samples.rsplit("/", 1)[0] + "/")
    input_dir = samples.rstrip(".zip") + "/"

    batch = 10
    file_total = 0
    file_count = 0
    tasks = []
    file_globs = []
    test_timer = time.time()
    for ext in extend(TYPE):
        file_total += len(glob.glob(input_dir + "**/*." + ext, recursive=True))
    for ext in extend(TYPE):
        file_globs.append(glob.iglob(input_dir + "**/*." + ext, recursive=True))

    if not single:
        file_total += file_total * batch
        for _ in range(batch):
            for ext in extend(TYPE):
                file_globs.append(glob.iglob(input_dir + "**/*." + ext, recursive=True))

    click.echo(f"Input: {input_dir} ({file_total} samples)")
    if limit:
        click.echo(f"Scan number limit: {limit}")
        file_total = limit

    if single:
        with Progress(
            SpinnerColumn(), MofNCompleteColumn(), *Progress.get_default_columns()
        ) as p:
            task_progress = p.add_task("[purple]Processing...", total=file_total)
            for files in file_globs:
                for path in files:
                    scan(path, mode=mode)
                    file_count += 1
                    p.update(task_progress, advance=1)
                    if p.finished:
                        break
                if p.finished:
                    break

    else:
        with Progress(
            SpinnerColumn(), MofNCompleteColumn(), *Progress.get_default_columns()
        ) as p:
            task_progress = p.add_task("[cyan]Sending task...", total=file_total)
            for files in file_globs:
                for path in files:
                    file_count += 1
                    p.update(task_progress, advance=1)
                    tasks.append(benchmark_task.remote(path, mode))
                    if p.finished:
                        break
                if p.finished:
                    break

        eta_step = 10  # ETA estimation interval
        ready, not_ready = ray.wait(tasks)

        with Progress(
            SpinnerColumn(), MofNCompleteColumn(), *Progress.get_default_columns()
        ) as p:
            task_progress = p.add_task("[cyan]Processing...", total=file_total)
            while not p.finished:
                if len(not_ready) < eta_step:
                    p.update(task_progress, completed=file_total)
                    continue
                tasks = not_ready
                ready, not_ready = ray.wait(tasks, num_returns=eta_step)
                p.update(task_progress, advance=len(ready))

        ray.get(tasks)

    shutil.rmtree(input_dir)

    test_timer = time.time() - test_timer
    sc = test_timer
    mn, sc = divmod(sc, 60)
    hr, mn = divmod(mn, 60)
    sc, mn, hr = int(sc), int(mn), int(hr)

    print("\n> Summary:")
    summary = {
        "File Processed": file_count,
        "Processing Time": f"{hr}h{mn}m{sc}s",
        "Throughput": f"{file_count/test_timer:.2f} file/sec",
        "System Info": {
            "python_version": get_cpu_info().get("python_version"),
            "brand_raw": get_cpu_info().get("brand_raw", None),
            "physical_cores:": psutil.cpu_count(logical=False),
            "total_threads:": psutil.cpu_count(logical=True),
            # "cpu_frequency": f"{psutil.cpu_freq().max:.2f}Mhz", # Not available on ARM based Mac
            "total_ram": f"{convert_ram(psutil.virtual_memory().total)}",
        },
    }
    # if int(psutil.cpu_freq().max) == 0:
    #     result['System Info'].update({"cpu_frequency": get_cpu_info().get("hz_advertised_friendly")})

    Console().print_json(json.dumps(summary))
    # with open("data/benchmark.json", "w") as f:
    #     json.dump(result, f)
    print("\n>> Benchmark Finished <<\n")


@ray.remote
def scan_task(path, output_dir, log_dir, mode, convert, target):
    try:
        result = scan(path, mode=mode, source=convert, target=target)
    except Exception as e:
        print(f">>>> Scan task error: {str(e)}")
        write_log(log_dir, {"file": path, "task error": str(e)})
        return

    if log := result.get("log", {}):
        log.update({"file": path})
        write_log(log_dir, log)
        result.pop("log")
    if log := result.get("converted", {}):
        log = {"convert": log}
        log.update({"file": path})
        write_log(log_dir, log)
        result.pop("converted")
    header = False if "error" in list(log.keys()) else True

    if result:
        write_csv(output_dir, result, header)


@ray.remote
def benchmark_task(path: str, mode: str) -> None:
    scan(path, mode=mode)
