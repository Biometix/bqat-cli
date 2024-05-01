import datetime
import glob
import json
import os
import shutil
import time
import warnings
from pathlib import Path
from uuid import uuid4
from zipfile import ZipFile

import click
import psutil
import ray
from cpuinfo import get_cpu_info
from PIL import Image, ImageOps
from rich.console import Console
from rich.progress import MofNCompleteColumn, Progress, SpinnerColumn
from rich.text import Text

from bqat import __version__ as version
from bqat.utils import (
    convert_ram,
    filter_output,
    generate_report,
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
    reporting: bool,
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
    engine: str,
    debugging: bool,
) -> None:
    if not debugging:
        ray.init(
            configure_logging=True,
            logging_level="error",
            log_to_driver=False,
        )

    warnings.simplefilter(action="ignore", category=FutureWarning)
    warnings.simplefilter(action="ignore", category=RuntimeWarning)
    warnings.simplefilter(action="ignore", category=UserWarning)

    TYPE = type if mode != "speech" else ["wav"]

    console = Console()
    metadata = Text("> Analyse:\n")
    metadata.append("\nMode: ")
    metadata.append(mode.upper(), style="bold yellow")
    if mode == "face":
        metadata.append("\nEngine: ")
        metadata.append(engine.upper(), style="bold yellow")
    metadata.append("\nInput Type: ")
    metadata.append(str(TYPE), style="bold yellow")
    if mode == "finger" and target:
        metadata.append("\nTarget Type: ")
        metadata.append(str(target), style="bold yellow")

    job_timer = time.time()

    if not os.path.exists(input_folder):
        click.echo(
            f">>> Input directory not found ({input_folder}). Check input path and make sure your `data/` folder mounted. Exit.\n"
        )
        return
    else:
        input_folder = validate_path(input_folder)

    file_total = 0
    for ext in extend(TYPE):
        file_total += len(
            glob.glob(input_folder + f"**/{pattern}." + ext, recursive=True)
        )

    metadata.append("\nInput Directory: ")
    metadata.append(input_folder, style="bold yellow")
    metadata.append(" (")
    metadata.append(str(file_total), style="bold yellow")
    metadata.append(" samples)\n")
    console.print(metadata)

    if limit:
        click.echo(f"Scan number limit: {limit}")
        if limit < file_total:
            file_total = limit

    if file_total == 0:
        click.echo(">>> No valid input found. Exit.\n")
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

    if mode == "face" and engine == "ofiq":
        with Progress(
            SpinnerColumn(), MofNCompleteColumn(), *Progress.get_default_columns()
        ) as p:
            task_progress = p.add_task("[purple]Processing...", total=file_total)
            tasks.append(
                scan_task.remote(
                    input_folder,
                    output_dir,
                    log_dir,
                    mode,
                    convert,
                    target,
                    engine,
                )
            )
            _, not_ready = ray.wait(tasks, timeout=3)
            while len(not_ready) != 0:
                count = 0
                if not Path("ofiq.log").exists():
                    continue
                with open("ofiq.log") as lines:
                    count = len([1 for _ in lines])
                    count //= 34
                advance = count - file_count
                if advance > 0:
                    file_count = count
                    p.update(task_progress, advance=advance)
                _, not_ready = ray.wait(not_ready, timeout=3)
                if p.finished:
                    break
            file_count = file_total
            p.update(task_progress, completed=file_count)
        ray.get(not_ready)

        # TODO: locale not configurable, UTC hardcoded.
        Console().log("[bold][red]Finished!")
    else:
        if single:
            with Progress(
                SpinnerColumn(), MofNCompleteColumn(), *Progress.get_default_columns()
            ) as p:
                task_progress = p.add_task("[purple]Processing...", total=file_total)
                for files in file_globs:
                    for path in files:
                        result = scan(
                            path,
                            mode=mode,
                            source=convert,
                            target=target,
                            type="file",
                            engine=engine,
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
            Console().log("[bold][red]Finished!")
        else:
            if mode != "speech":
                with Progress(
                    SpinnerColumn(),
                    MofNCompleteColumn(),
                    *Progress.get_default_columns(),
                ) as p:
                    task_progress = p.add_task(
                        "[cyan]Sending task...", total=file_total
                    )
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
                                    engine,
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
                    SpinnerColumn(),
                    MofNCompleteColumn(),
                    *Progress.get_default_columns(),
                ) as p:
                    task_progress = p.add_task("[cyan]Processing...", total=file_total)
                    while not p.finished:
                        if len(not_ready) < eta_step:
                            p.update(task_progress, completed=file_total)
                            continue
                        tasks = not_ready
                        ready, not_ready = ray.wait(tasks, num_returns=eta_step)
                        p.update(task_progress, advance=len(ready))

                ray.get(not_ready)
                Console().log("[bold][red]Finished!")
            else:
                dir_list = [
                    i
                    for i in Path(input_folder).rglob("*")
                    if (i.is_dir() and glob_path(i, TYPE))
                ]
                if glob_path(input_folder, TYPE, recursive=False):
                    dir_list.append(Path(input_folder))
                with Progress(
                    SpinnerColumn(),
                    MofNCompleteColumn(),
                    *Progress.get_default_columns(),
                ) as p:
                    task_progress = p.add_task("[cyan]Processing...", total=file_total)
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
                Console().log("[bold][red]Finished!")

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
        if output_dir and reporting:
            write_report(report_dir, output_dir, f"EDA Report (BQAT v{version})")
        else:
            report_dir = None
    except Exception as e:
        report_dir = None
        click.echo(f"failed to generate report: {str(e)}")

    try:
        if output_dir and (attributes or query or sort):
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
            # "Failed": failed_count,
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
            {
                "Table": dir.get("table"),
                "Output": dir.get("output"),
                "Report": dir.get("report"),
            }
            if dir
            else False
        )
    except Exception as e:
        click.echo(f"failed to apply filter: {str(e)}")
        dir = {}
        outlier_filter = False
    if outlier_filter:
        print("\n> Summary:")
        summary = {"Output Filter": outlier_filter}
        Console().print_json(json.dumps(summary))
    print("\n>> Finished <<\n")
    return dir


def benchmark(mode: str, limit: int, single: bool, engine: str) -> None:
    """Run benchmark to profile the capability of host system."""
    ray.init(
        configure_logging=True,
        logging_level="error",
        log_to_driver=False,
    )

    console = Console()
    metadata = Text(">> Benchmarking Started <<")
    metadata.append("\n\nMode: ")
    metadata.append(mode.upper(), style="bold yellow")
    if mode == "face":
        metadata.append("\nEngine: ")
        metadata.append(engine.upper(), style="bold yellow")

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
        if mode == "face" and engine == "ofiq":
            for files in file_globs:
                for path in files:
                    path = Path(path)
                    for i in range(batch):
                        shutil.copy(path, path.parent / f"{i}_{path.name}")
        elif mode != "iris":
            for _ in range(batch):
                for ext in extend(TYPE):
                    file_globs.append(
                        glob.iglob(input_dir + "**/*." + ext, recursive=True)
                    )
        else:
            for i in range(batch):
                with ZipFile(samples, "r") as z:
                    z.extractall(f"{input_dir}batch_{i}/")
            file_globs.append(glob.iglob(input_dir + "**/*." + ext, recursive=True))

    metadata.append("\nInput: ")
    metadata.append(input_dir, style="bold yellow")
    metadata.append(" (")
    metadata.append(str(file_total), style="bold yellow")
    metadata.append(" samples)\n")
    console.print(metadata)

    if limit:
        click.echo(f"Scan number limit: {limit}")
        file_total = limit

    if mode == "face" and engine == "ofiq":
        with Progress(
            SpinnerColumn(), MofNCompleteColumn(), *Progress.get_default_columns()
        ) as p:
            task_progress = p.add_task("[purple]Processing...", total=file_total)
            tasks.append(
                benchmark_task.remote(
                    input_dir,
                    mode,
                    engine,
                )
            )
            _, not_ready = ray.wait(tasks, timeout=3)
            while len(not_ready) != 0:
                count = 0
                if not Path("ofiq.log").exists():
                    continue
                with open("ofiq.log") as lines:
                    count = len([1 for _ in lines])
                    count //= 34
                advance = count - file_count
                if advance > 0:
                    file_count = count
                    p.update(task_progress, advance=advance)
                _, not_ready = ray.wait(not_ready, timeout=3)
                if p.finished:
                    break
            file_count = file_total
            p.update(task_progress, completed=file_count)
        ray.get(not_ready)

        Console().log("[bold][red]Finished!")
    else:
        if single:
            with Progress(
                SpinnerColumn(), MofNCompleteColumn(), *Progress.get_default_columns()
            ) as p:
                task_progress = p.add_task("[purple]Processing...", total=file_total)
                for files in file_globs:
                    for path in files:
                        scan(path, mode=mode, type="file", engine=engine)
                        file_count += 1
                        p.update(task_progress, advance=1)
                        if p.finished:
                            break
                    if p.finished:
                        break

        else:
            if mode != "speech":
                with Progress(
                    SpinnerColumn(),
                    MofNCompleteColumn(),
                    *Progress.get_default_columns(),
                ) as p:
                    task_progress = p.add_task(
                        "[cyan]Sending task...", total=file_total
                    )
                    for files in file_globs:
                        for path in files:
                            file_count += 1
                            p.update(task_progress, advance=1)
                            tasks.append(benchmark_task.remote(path, mode, engine))
                            if p.finished:
                                break
                        if p.finished:
                            break

                eta_step = 10  # ETA estimation interval
                ready, not_ready = ray.wait(tasks)

                with Progress(
                    SpinnerColumn(),
                    MofNCompleteColumn(),
                    *Progress.get_default_columns(),
                ) as p:
                    task_progress = p.add_task(
                        "[cyan]Processing...\n", total=file_total
                    )
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
                        file_count += len(out.get("results"))
                    Console().log("[bold][red]Finished!")
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
    print("\n>> Benchmarking Finished <<\n")


@ray.remote
def scan_task(path, output_dir, log_dir, mode, convert, target, engine):
    if engine != "ofiq":
        try:
            result = scan(path, mode=mode, source=convert, target=target, engine=engine)
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
    else:
        try:
            result = scan(path, mode=mode, engine=engine)
        except Exception as e:
            print(f">>>> Scan task error: {str(e)}")
            write_log(log_dir, {"folder": path, "task error": str(e)})
            return

        log = {}
        if result.get("log"):
            log = result.pop("log")
            log.update({"folder": path})
            write_log(log_dir, log)

        result_list = result.get("results")
        for result in result_list:
            write_csv(output_dir, result)


@ray.remote
def benchmark_task(path: str, mode: str, engine: str) -> None:
    if mode == "finger":
        scan(
            path, mode=mode, source="na", target="na"
        )  # Specify a dummy type so no conversion
    else:
        print(scan(path, mode=mode, engine=engine))


def report(input, cwd):
    try:
        dir = generate_report(input, cwd)
        report = (
            {"Table": dir.get("table"), "Report": dir.get("report")} if dir else False
        )
    except Exception as e:
        click.echo(f"failed to generate report: {str(e)}")
        dir = {}
        report = False
    if report:
        print("\n> Summary:")
        summary = {"EDA Report": report}
        Console().print_json(json.dumps(summary))
    print("\n>> Finished <<\n")
    return dir


def preprocess(input_dir: str, output_dir: str, debugging: bool, config: dict) -> str:
    if not debugging:
        ray.init(
            configure_logging=True,
            logging_level="error",
            log_to_driver=False,
        )
    file_total = 0
    file_count = 0
    tasks = []
    file_globs = []
    task_timer = time.time()
    TYPE = config.get("source", ["wsq", "jpg", "jpeg", "png", "bmp", "jp2"])

    if not os.path.exists(input_dir):
        click.echo(
            f">>> Input directory not found ({input_dir}). Check input path and make sure your `data/` folder mounted. Exit.\n"
        )
        return
    else:
        input_dir = validate_path(input_dir)

    if not output_dir:
        output_dir = Path(input_dir) / f"{str(uuid4())}"

    for ext in extend(TYPE):
        file_total += len(glob.glob(input_dir + "**/*." + ext, recursive=True))
    for ext in extend(TYPE):
        file_globs.append(glob.iglob(input_dir + "**/*." + ext, recursive=True))

    console = Console()
    metadata = Text(">> Preprocessing Task Started <<\n")
    metadata.append("\nInput: ")
    metadata.append(input_dir, style="bold yellow")
    metadata.append(" (")
    metadata.append(str(file_total), style="bold yellow")
    metadata.append(" samples)\n")

    configs = 0

    if target := config.get("target"):
        metadata.append("\nConvert to: ")
        metadata.append(target.upper(), style="bold yellow")
        configs += 1
    if config.get("grayscale"):
        metadata.append("\nConvert to: ")
        metadata.append("Grayscale (8-bit pixels, grayscale)", style="bold yellow")
        configs += 1
    if config.get("rgb"):
        metadata.append("\nConvert to: ")
        metadata.append("RGB (3x8-bit pixels, true color)", style="bold yellow")
        configs += 1
    if width := config.get("width"):
        metadata.append("\nResize by width: ")
        metadata.append(f"{str(width)} pixels", style="bold yellow")
        configs += 1
    if frac := config.get("frac"):
        metadata.append("\nResize by percentage: ")
        metadata.append(f"{int(frac*100)}%", style="bold yellow")
        configs += 1

    metadata.append("\n")
    console.print(metadata)

    if file_total == 0:
        click.echo(">>> No valid input file. Exit.\n")
        return

    if configs == 0:
        click.echo(">>> No preprocessing task specified. Exit.\n")
        return

    with Progress(
        SpinnerColumn(), MofNCompleteColumn(), *Progress.get_default_columns()
    ) as p:
        task_progress = p.add_task("[cyan]Sending task...", total=file_total)
        for files in file_globs:
            for path in files:
                file_count += 1
                p.update(task_progress, advance=1)
                try:
                    tasks.append(
                        preprocess_task.remote(
                            path,
                            output_dir,
                            config,
                        )
                    )
                except Exception as e:
                    click.echo(f"Preprocessing task failed: {e}")
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
    Console().log("[bold][red]Finished!")

    task_timer = time.time() - task_timer
    sc = task_timer
    mn, sc = divmod(sc, 60)
    hr, mn = divmod(mn, 60)
    sc, mn, hr = int(sc), int(mn), int(hr)

    print("\n> Summary:")
    summary = {
        "File Count": file_count,
        "Time Elapsed": f"{hr}h{mn}m{sc}s",
        "Throughput": f"{file_count/task_timer:.2f} item/sec",
        "Preprocessing Task": {
            "Processed": file_count,
            "Output": str(output_dir),
        },
    }
    Console().print_json(json.dumps(summary))
    print("\n>> Preprocessing Task Finished <<\n")


@ray.remote
def preprocess_task(file: str, output: dir, config: dict) -> None:
    try:
        file = Path(file)
        if not Path(output).exists():
            Path(output).mkdir(parents=True, exist_ok=True)
        with Image.open(file) as img:
            if config.get("grayscale", False):
                img = ImageOps.grayscale(img)
                # img = img.convert("L")
            if config.get("rbg", False):
                img = img.convert("RGB")

            if width := config.get("width", False):
                height = int(width * img.height / img.width)
                img = img.resize((width, height))
            if frac := config.get("frac", False):
                img = img.resize((int(img.width * frac), int(img.height * frac)))

            if target := config.get("target", False):
                processed = Path(output) / f"{file.stem}.{target}"
            else:
                processed = Path(output) / file.name
            img.save(processed)
    except Exception as e:
        print(f">>>> Preprocess task error: {str(e)}")
