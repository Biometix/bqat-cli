import asyncio
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
from rich.panel import Panel
from rich.progress import MofNCompleteColumn, Progress, SpinnerColumn, TimeElapsedColumn
from rich.table import Table
from rich.text import Text

from bqat import __version__ as version
from bqat.utils import (
    convert_ram,
    extended,
    filter_output,
    fix_filepath,
    generate_report,
    iter_matching_files,
    reconstruct_filepath,
    split_input_folder,
    validate_path,
    write_csv,
    write_log,
)

from .core.bqat_core import scan


async def run(
    mode: str,
    input_folder: str,
    output_folder: str,
    reporting: bool,
    # report_dir: str,
    # log_dir: str,
    limit: int,
    pattern: str,
    type: list,
    convert: list,
    target: str,
    attributes: str,
    query: str,
    sort: str,
    cwd: str,
    prefix: str,
    batch: int,
    fusion: int,
    engine: str,
    debug: bool,
) -> None:
    if not debug:
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
    metadata = Table(show_header=False, box=None)
    metadata.add_row("Mode", f"[bold yellow]{mode.upper()}")
    if mode == "face":
        metadata.add_row("Engine", f"[dark_goldenrod]{engine.upper()}")
    if engine == "fusion":
        metadata.add_row("Fusion Code", f"[dark_goldenrod]{str(fusion)}")
    metadata.add_row("Input Type", f"[dark_goldenrod]{str(TYPE)}")
    if mode == "finger" and target:
        metadata.add_row("Target Type", f"[dark_goldenrod]{str(target)}")

    job_timer = time.time()

    if not os.path.exists(input_folder):
        click.echo(
            f">>> Input directory not found ({input_folder}). Check input path and make sure your `data/` folder mounted. Exit.\n"
        )
        return
    else:
        input_folder = validate_path(input_folder)

    file_total = sum(
        1 for _ in iter_matching_files(input_folder, pattern, extended(TYPE))
    )

    metadata.add_row("Input Folder", f"[dark_goldenrod]{prefix + input_folder}")
    metadata.add_row("Input Count", f"[bold yellow]{str(file_total)}")

    console.print(
        Panel(
            metadata,
            title="[white]Job Info[/white]",
            expand=False,
        )
    )

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
    output_dir = output_folder + f"output_{mode}_{engine}_{timestamp}.csv"
    log_dir = output_folder + f"log_{mode}_{engine}_{timestamp}.json"
    report_dir = output_folder + f"report_{mode}_{engine}_{timestamp}.html"

    write_csv(output_dir, init=True)
    write_log(log_dir, init=True)

    file_globs = iter_matching_files(input_folder, pattern, extended(TYPE))

    file_count = 0
    failed = 0
    tasks = []

    if mode == "speech" or (mode == "face" and engine in ("ofiq", "fusion")):
        with Console().status("Prepare input folders..."):
            temp_folder = f"temp/{int(time.time())}"
            Path(temp_folder).mkdir()
            input_folders = split_input_folder(
                input_folder=input_folder,
                temp_folder=temp_folder,
                exts=extended(TYPE),
                batch_size=batch,
                pattern=pattern,
                limit=limit,
            )

        with Progress(
            SpinnerColumn(),
            MofNCompleteColumn(),
            TimeElapsedColumn(),
            *Progress.get_default_columns(),
        ) as p:
            task_progress = p.add_task("[purple]Processing...", total=file_total)
            for folder in input_folders:
                tasks.append(
                    scan_task.remote(
                        folder,
                        output_dir,
                        log_dir,
                        mode,
                        convert,
                        target,
                        engine,
                        fusion=fusion,
                        prefix=prefix,
                    )
                )
                not_ready = True
                while not_ready:
                    ready, not_ready = ray.wait(tasks, timeout=0.1)
                    await asyncio.sleep(3)
                if ray.get(ready)[0]:
                    file_count += batch
                    if file_count > file_total:
                        batch = file_total - file_count + batch
                        file_count = file_total
                    p.update(task_progress, advance=batch)
                else:
                    failed += batch
                tasks = []
            shutil.rmtree(temp_folder)
    else:
        with Progress(
            SpinnerColumn(),
            MofNCompleteColumn(),
            TimeElapsedColumn(),
            *Progress.get_default_columns(),
        ) as p:
            task_progress = p.add_task("[cyan]Sending task...", total=file_total)
            for path in file_globs:
                tasks.append(
                    scan_task.remote(
                        path.as_posix(),
                        output_dir,
                        log_dir,
                        mode,
                        convert,
                        target,
                        engine,
                        prefix=prefix,
                    )
                )
                file_count += 1
                p.update(task_progress, advance=1)
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
            TimeElapsedColumn(),
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
                "engine": engine,
                "mode": mode,
                "processed": file_count,
                "failed": 0,
                "log": None,
                "process time": f"{hr}h{mn}m{sc}s",
            }
        }
        if engine == "fusion":
            log_out["metadata"].update({"fusion": fusion})
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
            # write_report(report_dir, output_dir, f"EDA Report (BQAT v{version})")
            dir = generate_report(output_dir, cwd, prefix)
            report_dir = (
                {"Preview Table": dir.get("table"), "EDA Report": dir.get("report")}
                if dir
                else False
            )
        else:
            report_dir = None
    except Exception as e:
        report_dir = None
        click.echo(f"failed to generate report: {str(e)}")

    try:
        if output_dir and (attributes or query or sort):
            dir = filter_output(output_dir, attributes, query, sort, cwd, prefix)
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

    Console().print("\n> Summary:")
    summary = {
        "Total process time": f"{hr}h{mn}m{sc}s",
        "System throughput": f"{file_count / job_timer:.2f} it/s",
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
    Console().print("\n>> [bright_yellow]Task Finished[/bright_yellow] <<\n")


def filter(output, attributes, query, sort, cwd, prefix):
    try:
        dir = filter_output(output, attributes, query, sort, cwd, prefix)
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
    Console().print("\n>> [bright_yellow]Task Finished[/bright_yellow] <<\n")
    return dir


async def benchmark(
    mode: str,
    limit: int,
    engine: str,
    fusion: int,
    batch: int,
) -> None:
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
    if engine == "fusion":
        metadata.append("\nFusion Code: ")
        metadata.append(str(fusion), style="bold yellow")

    TYPE = ("wsq", "jpg", "jpeg", "png", "bmp", "jp2")

    if mode == "fingerprint" or mode == "finger":
        samples = "tests/samples/finger.zip"
    elif mode == "face":
        samples = "tests/samples/face.zip"
    elif mode == "iris":
        samples = "tests/samples/iris.zip"
    elif mode == "speech":
        TYPE = ("wav",)
        samples = "tests/samples/speech.zip"
    else:
        raise RuntimeError(f"{mode} not support")

    with ZipFile(samples, "r") as z:
        z.extractall(samples.rsplit("/", 1)[0] + "/")
    input_dir = samples.rstrip(".zip") + "/"

    repeat = 99
    file_total = 0
    file_count = 0
    tasks = []
    file_globs = []
    test_timer = time.time()
    for ext in extended(TYPE):
        file_total += len(glob.glob(input_dir + "**/*." + ext, recursive=True))
    for ext in extended(TYPE):
        file_globs.append(glob.iglob(input_dir + "**/*." + ext, recursive=True))

    file_total += file_total * repeat
    if mode in ("iris", "speech") or (mode == "face" and engine in ("ofiq", "fusion")):
        for i in range(repeat):
            with ZipFile(samples, "r") as z:
                z.extractall(f"{input_dir}batch_{i}/")
            for ext in extended(TYPE):
                file_globs.append(glob.iglob(input_dir + "**/*." + ext, recursive=True))
    else:
        for _ in range(repeat):
            for ext in extended(TYPE):
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

    if mode == "speech" or (mode == "face" and engine in ("ofiq", "fusion")):
        with Console().status("Prepare input folders..."):
            temp_folder = f"temp/{int(time.time())}"
            Path(temp_folder).mkdir()
            input_folders = split_input_folder(
                input_folder=input_dir,
                temp_folder=temp_folder,
                exts=extended(TYPE),
                batch_size=batch,
                limit=limit,
            )

        with Progress(
            SpinnerColumn(),
            MofNCompleteColumn(),
            TimeElapsedColumn(),
            *Progress.get_default_columns(),
        ) as p:
            task_progress = p.add_task("[purple]Processing...", total=file_total)
            for folder in input_folders:
                tasks.append(
                    benchmark_task.remote(
                        folder,
                        mode,
                        engine,
                        fusion,
                    )
                )
                not_ready = True
                while not_ready:
                    ready, not_ready = ray.wait(tasks, timeout=0.1)
                    await asyncio.sleep(3)

                file_count += batch
                if file_count > file_total:
                    batch = file_total - file_count + batch
                    file_count = file_total
                p.update(task_progress, advance=batch)

                tasks = []
            shutil.rmtree(temp_folder)
    else:
        with Progress(
            SpinnerColumn(),
            MofNCompleteColumn(),
            TimeElapsedColumn(),
            *Progress.get_default_columns(),
        ) as p:
            task_progress = p.add_task("[cyan]Sending task...", total=file_total)
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
            TimeElapsedColumn(),
            *Progress.get_default_columns(),
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
        "Throughput": f"{file_count / test_timer:.2f} it/s",
        "System Info": {
            "python_version": get_cpu_info().get("python_version"),
            "cpu_vendor": get_cpu_info().get("vendor_id_raw", None),
            "cpu_name": get_cpu_info().get("brand_raw", None),
            "cpu_arch": get_cpu_info().get("arch_string_raw", None),
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
    Console().print("\n>> Benchmarking Finished <<\n")


@ray.remote
def scan_task(
    path,
    output_dir,
    log_dir,
    mode,
    convert,
    target,
    engine,
    fusion=6,
    prefix="",
):
    results = []
    if mode == "speech" or (mode == "face" and engine in ("ofiq", "fusion")):
        try:
            result = scan(path, mode=mode, engine=engine, fusion=fusion)
            result_list = result.get("results")
        except Exception as e:
            print(f">>>> Scan task error: {str(e)}")
            write_log(log_dir, {"folder": path, "task error": str(e)})
            return

        for result in result_list:
            result = fix_filepath(result)
            result = reconstruct_filepath(result, prefix)
            if result.get("log"):
                log_dict = {"folder": path, "logs": result.pop("log")}
                write_log(log_dir, log_dict)
            write_csv(output_dir, result)
            results.append(result)
    else:
        try:
            result = scan(path, mode=mode, source=convert, target=target, engine=engine)
        except Exception as e:
            print(f">>>> Scan task error: {str(e)}")
            write_log(log_dir, {"file": path, "task error": str(e)})
            return

        if result.get("log"):
            logs = result.pop("log")
            for log in logs:
                log.update({"file": path})
                write_log(log_dir, log)
        result = reconstruct_filepath(result, prefix)
        write_csv(output_dir, result)
        results.append(result)
    return results


@ray.remote
def benchmark_task(path: str, mode: str, engine: str, fusion=6) -> None:
    if mode == "finger":
        scan(
            path,
            mode=mode,
            source="na",
            target="na",
        )  # Specify a dummy type so no conversion
    else:
        scan(
            path,
            mode=mode,
            engine=engine,
            fusion=fusion,
        )


def report(input, cwd, prefix):
    try:
        dir = generate_report(input, cwd, prefix)
        report = (
            {"Preview Table": dir.get("table"), "EDA Report": dir.get("report")}
            if dir
            else False
        )
    except Exception as e:
        click.echo(f"failed to generate report: {str(e)}")
        dir = {}
        report = False
    if report:
        print("\n> Summary:")
        summary = {"EDA Report": report}
        Console().print_json(json.dumps(summary))
    Console().print("\n>> [bright_yellow]Task Finished[/bright_yellow] <<\n")
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

    for ext in extended(TYPE):
        file_total += len(glob.glob(input_dir + "**/*." + ext, recursive=True))
    for ext in extended(TYPE):
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
        SpinnerColumn(),
        MofNCompleteColumn(),
        TimeElapsedColumn(),
        *Progress.get_default_columns(),
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
        SpinnerColumn(),
        MofNCompleteColumn(),
        TimeElapsedColumn(),
        *Progress.get_default_columns(),
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
    Console().print(
        "\n>> [bright_yellow]Preprocessing Task Finished[/bright_yellow] <<\n"
    )


@ray.remote
def preprocess_task(file: str, output: dir, config: dict) -> None:
    try:
        import wsq
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
