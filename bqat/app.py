import datetime
import glob
import json
import os
import shutil
import time
import warnings
from pathlib import Path
from zipfile import ZipFile

import click
import psutil
import ray
from cpuinfo import get_cpu_info
from rich.console import Console
from rich.progress import MofNCompleteColumn, Progress, SpinnerColumn

from bqat import __version__ as version
from bqat.utils import (
    convert_ram,
    filter_output,
    glob_path,
    validate_path,
    write_csv,
    write_log,
    write_report,
)

from .core.bqat_core import scan
from .core.bqat_core.utils import extend


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
    cwd: str,
) -> None:
    warnings.simplefilter(action="ignore", category=FutureWarning)
    warnings.simplefilter(action="ignore", category=RuntimeWarning)
    warnings.simplefilter(action="ignore", category=UserWarning)

    TYPE = type if mode != "speech" else ["wav"]

    print("> Analyse:")
    click.echo(f"Mode: {mode.upper()}")
    job_timer = time.time()

    if not os.path.exists(input_folder):
        click.echo(
            "Input directory not found. Make sure your local `data/` folder mounted.\n"
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
        click.echo("Exit. No valid input file.\n")
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
    failed = 0
    tasks = []

    if single:
        with Progress(
            SpinnerColumn(), MofNCompleteColumn(), *Progress.get_default_columns()
        ) as p:
            task_progress = p.add_task("[purple]Scanning...", total=file_total)
            for files in file_globs:
                for path in files:
                    result = scan(
                        path,
                        mode=mode,
                        source=convert,
                        target=target,
                        type="file",
                    )

                    log = {}
                    if result.get("converted"):
                        log = {"convert": result.get("converted")}
                        log.update({"file": path})
                        write_log(log_dir, log)
                        result.pop("converted")
                    if result.get("log"):
                        log = result.pop("log")
                        log.update({"file": path})
                        write_log(log_dir, log)

                    if not log.get("load image"):
                        write_csv(output_dir, result)

                    file_count += 1
                    p.update(task_progress, advance=1)
                    if p.finished:
                        break
                if p.finished:
                    break
        Console().log("[bold][red]Done!")
    else:
        if mode != "speech":
            with Progress(
                SpinnerColumn(), MofNCompleteColumn(), *Progress.get_default_columns()
            ) as p:
                task_progress = p.add_task("[cyan]Sending task...", total=file_total)
                for files in file_globs:
                    for path in files:
                        tasks.append(
                            scan_task.remote(
                                path,
                                output_dir,
                                log_dir,
                                mode,
                                convert,
                                target,
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
            Console().log("[bold][red]Done!")
        else:
            dir_list = [
                i
                for i in Path(input_folder).rglob("*")
                if (i.is_dir() and glob_path(i, TYPE))
            ]
            if glob_path(input_folder, TYPE, recursive=False):
                dir_list.append(Path(input_folder))
            with Progress(
                SpinnerColumn(), MofNCompleteColumn(), *Progress.get_default_columns()
            ) as p:
                task_progress = p.add_task("[cyan]Scanning...", total=file_total)
                for dir in dir_list:
                    ready = 0
                    try:
                        output = scan(dir, mode=mode, type="folder")
                        if output.get("log"):
                            log = output.pop("log")
                            log.update({"directory": str(dir)})
                            write_log(log_dir, log)
                        result_list = output["results"]
                        for result in result_list:
                            ready += 1
                            write_csv(output_dir, result)
                    except Exception as e:
                        ready = len(glob_path(str(dir), TYPE, recursive=False))
                        failed += ready
                        error = json.loads(str(e))
                        log = {
                            "directory": str(dir),
                            "file count": ready,
                            "error": error,
                        }
                        write_log(log_dir, log)
                    p.update(task_progress, advance=ready)
                    file_count += ready
                    if p.finished:
                        break
            Console().log("[bold][red]Done!")

    job_timer = time.time() - job_timer
    sc = job_timer
    mn, sc = divmod(sc, 60)
    hr, mn = divmod(mn, 60)
    sc, mn, hr = int(sc), int(mn), int(hr)

    try:
        write_log(log_dir, finish=True)
        log_out = {
            "metadata": {
                "version": "BQAT v" + version,
                "datetime": str(dt),
                "input directory": input_folder,
                "processed": file_count,
                "failed": 0,
                "log": None,
                "process time": f"{hr}h{mn}m{sc}s",
            }
        }
        with open(log_dir, "r") as f:
            logs = json.load(f)
            log_out["metadata"].update({"log": len(logs)})
            log_out["log"] = logs
            log_out["metadata"]["failed"] = (
                failed_count := len([item for item in logs if item.get("load image")])
                if not failed
                else failed
            )
        with open(log_dir, "w") as f:
            json.dump(log_out, f)
    except Exception as e:
        click.echo(f"failed to reload metadata for log: {str(e)}")

    if file_count == failed_count:
        output_dir = None
        report_dir = None

    try:
        if output_dir:
            write_csv(output_dir, seam=True)
    except Exception as e:
        click.echo(f"failed to seam output: {str(e)}")

    try:
        if output_dir:
            write_report(report_dir, output_dir, f"EDA Report (BQAT v{version})")
        else:
            report_dir = None
    except Exception as e:
        report_dir = None
        click.echo(f"failed to generate report: {str(e)}")

    try:
        if output_dir:
            dir = filter_output(output_dir, attributes, query, sort, cwd)
            outlier_filter = (
                {"Output": dir.get("output"), "Report": dir.get("report")}
                if dir
                else False
            )
        else:
            outlier_filter = None
    except Exception as e:
        click.echo(f"failed to apply filter: {str(e)}")
        outlier_filter = None

    print("\n> Summary:")
    summary = {
        "Total process time": f"{hr}h{mn}m{sc}s",
        "System throughput": f"{file_count/job_timer:.2f} item/s",
        "Assessment Task": {
            "Processed": file_count,
            "Failed": failed_count,
            "Input": input_folder,
            "Output": output_dir,
            "Report": report_dir,
            "Log": log_dir,
        },
    }
    if outlier_filter:
        summary.update({"Outlier Filter": outlier_filter})

    Console().print_json(json.dumps(summary))
    print("\n>> Finished <<\n")


def filter(output, attributes, query, sort, cwd):
    try:
        dir = filter_output(output, attributes, query, sort, cwd)
        outlier_filter = (
            {"Output": dir.get("output"), "Report": dir.get("report")} if dir else False
        )
    except Exception as e:
        click.echo(f"failed to apply filter: {str(e)}")
        dir = {}
        outlier_filter = False
    if outlier_filter:
        print("\n> Summary:")
        summary = {"Outlier Filter": outlier_filter}
        Console().print_json(json.dumps(summary))
    print("\n>> Finished <<\n")
    return dir


def benchmark(mode: str, limit: int, single: bool) -> None:
    """Run benchmark to profile the capability of host system."""
    click.echo(">> Start Benchmark <<\n")
    click.echo(f"Mode: {mode.upper()}")

    TYPE = ["wsq", "jpg", "jpeg", "png", "bmp", "jp2"]

    if mode == "fingerprint" or mode == "finger":
        samples = "tests/samples/finger.zip"
    elif mode == "face":
        samples = "tests/samples/face.zip"
    elif mode == "iris":
        samples = "tests/samples/iris.zip"
    elif mode == "speech":
        TYPE = ["wav"]
        samples = "tests/samples/speech.zip"
    else:
        raise RuntimeError(f"{mode} not support")

    with ZipFile(samples, "r") as z:
        z.extractall(samples.rsplit("/", 1)[0] + "/")
    input_dir = samples.rstrip(".zip") + "/"

    batch = 99
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

    click.echo(f"Input: {input_dir} ({file_total} samples)\n")
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
                    scan(path, mode=mode, type="file")
                    file_count += 1
                    p.update(task_progress, advance=1)
                    if p.finished:
                        break
                if p.finished:
                    break

    else:
        if mode != "speech":
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
                task_progress = p.add_task("[cyan]Processing...\n", total=file_total)
                while not p.finished:
                    if len(not_ready) < eta_step:
                        p.update(task_progress, completed=file_total)
                        continue
                    tasks = not_ready
                    ready, not_ready = ray.wait(tasks, num_returns=eta_step)
                    p.update(task_progress, advance=len(ready))

            ray.get(tasks)
        else:
            try:
                input_file = glob.glob(input_dir + "*.wav")[0]
                for index in range(batch):
                    shutil.copy(input_file, input_dir + f"input_file_{index}.wav")
                with Console().status("[bold green]Processing data...") as _:
                    out = scan(input_dir, mode=mode, type="folder")
                    file_count += len(out)
                Console().log("[bold][red]Done!")
            except Exception as e:
                print(str(e))

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

    log = {}
    if result.get("converted"):
        log = {"convert": result.get("converted")}
        log.update({"file": path})
        write_log(log_dir, log)
        result.pop("converted")
    if result.get("log"):
        log = result.pop("log")
        log.update({"file": path})
        write_log(log_dir, log)

    if not log.get("load image"):
        write_csv(output_dir, result)


@ray.remote
def benchmark_task(path: str, mode: str) -> None:
    if mode == "finger":
        scan(
            path, mode=mode, source="na", target="na"
        )  # Specify a dummy type so no conversion
    else:
        scan(path, mode=mode)
