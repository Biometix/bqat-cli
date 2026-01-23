import asyncio
import time
from pathlib import Path

import click
from rich.console import Console
from rich.panel import Panel

from bqat import __build__ as build
from bqat import __name__ as name
from bqat import __version__ as version
from bqat.app import benchmark as benchmark_job
from bqat.app import filter as filter_job
from bqat.app import preprocess as preprocess_job
from bqat.app import report as report_job
from bqat.app import run as assessment_job

# from bqat.utils import menu

INPUT_TYPE = ["wsq", "jpg", "jpeg", "png", "bmp", "jp2"]
PROC_TYPE = [
    "wsq",
    "jpg",
    "jpeg",
    "png",
    "bmp",
    "jp2",
    "gif",
    "tiff",
    "tif",
    "ppm",
    "pgm",
    "pbm",
    "pnm",
    "webp",
    "avif",
]


@click.command(
    epilog="See https://biometix.github.io/playbook/cli.html for more details"
)
@click.option(
    "--mode",
    "-M",
    default="face",
    help="Specify BQAT running mode (Fingerprint, Face, Iris, Speech).",
)
@click.option(
    "--input",
    "-I",
    default="data/",
    help="Specify input directory or CSV file for analysis.",
)
@click.option(
    "--output",
    "-O",
    default="",
    help="Specify output directory.",
)
@click.option(
    "--report",
    "-R",
    is_flag=True,
    default=False,
    help="Enable reporting.",
)
# @click.option(
#     "--log",
#     "-L",
#     default="data/output/",
#     help="Specify log directory.")
@click.option(
    "--benchmark",
    "-B",
    is_flag=True,
    default=False,
    help="Run system benchmarking analysis.",
)
@click.option(
    "--limit",
    "-L",
    type=int,
    default=0,
    help="Set a limit for number of files to scan.",
)
@click.option(
    "--filename",
    "-F",
    default="*",
    help="Filename pattern to search within the input folder.",
)
@click.option(
    "--type",
    default="",
    help="Specify file types to process in the input folder ('[type_1],[type_2],[type_3]').",
)
@click.option(
    "--convert",
    "-C",
    default="",
    help="Specify file formats to convert before processing (fingerprint only, '[type_1],[type_2],[type_3]').",
)
@click.option(
    "--target",
    "-T",
    default="",
    help="Specify target format to convert to (fingerprint only).",
)
# @click.option(
#     "--interactive",
#     "-X",
#     is_flag=True,
#     default=False,
#     help="Enter terminal interactive ui.",
# )
@click.option(
    "--columns",
    default="",
    help="Select columns to investigate.",
)
@click.option(
    "--query",
    "-Q",
    default="",
    help="Queries to apply on the columns ('[pandas query]').",
)
@click.option(
    "--sort",
    default="",
    help="Specify columns to sort by.",
)
@click.option(
    "--cwd",
    "-W",
    default="",
    help="Specify current working directory for url.",
)
@click.option(
    "--prefix",
    "-P",
    default="",
    help="Specify cwd prefix for file path reconstruction.",
)
@click.option(
    "--batch",
    default=30,
    help="Fusion mode processing batch size.",
)
@click.option(
    "--fusion",
    default=6,
    help="Specify engine code for fusion mode (BQAT:4, OFIQ:2, BIQT:1).",
)
@click.option(
    "--engine",
    "-E",
    default="bqat",
    help="Specify alternative face processing engine (BQAT, OFIQ, BIQT, Fusion).",
)
@click.option(
    "--config",
    default="",
    help='Configure preprocessing task ("[target format],[target width],[color mode (grayscale, rgb)]").',
)
@click.option(
    "--debug",
    is_flag=True,
    default=False,
    help="Enable debugging mode (print out runtime logs).",
)
def main(
    input,
    output,
    report,
    # log,
    benchmark,
    mode,
    limit,
    filename,
    type,
    convert,
    target,
    # interactive,
    columns,
    query,
    sort,
    cwd,
    prefix,
    batch,
    fusion,
    engine,
    config,
    debug,
):
    console = Console()
    console.print("")
    console.rule(
        f"[bold dark_red]{name}[/bold dark_red]",
        style="white",
    )
    console.print(Panel.fit(f"Version: {version}, Build: {build}"))
    console.print("")

    if query and columns:
        if not len([True for col in columns.split(",") if col in query]):
            click.echo(
                f'>>> Query ("{query}") invalid for selected columns ({columns.split(",")}). Exit.\n'
            )
            return

    cwd = Path(cwd).as_posix()

    # if interactive:
    #     selections = menu()
    #     for k, v in selections.items():
    #         if k == "mode":
    #             mode = v
    #         if k == "benchmark":
    #             benchmarking = v
    #         if k == "input":
    #             input = v
    #         if k == "output":
    #             output = v
    #             # report = v
    #             # log = v
    #         if k == "limit":
    #             limit = v
    #         if k == "filename":
    #             filename = v
    #         if k == "arm":
    #             arm = v
    #         if k == "search":
    #             search = v
    #         if k == "convert":
    #             convert = v
    #         if k == "target":
    #             target = v
    #     click.echo("")

    engine = engine.casefold()
    if engine not in (
        "bqat",
        "ofiq",
        "biqt",
        "fusion",
    ):
        click.echo(f">>> Engine [{engine}] not recognised. Exit.\n")
        return

    if fusion not in (
        7,
        6,
        5,
        # 4,
        3,
        # 2,
        # 1,
    ):
        click.echo(
            f">>> Engine fusion code [{fusion}] not recognised (e.g. 7, 6, 5, 3). Exit.\n"
        )
        return

    mode = mode.casefold()
    if mode not in (
        "",
        "face",
        "finger",
        "fingerprint",
        "iris",
        "speech",
        "filter",
        "report",
        "preprocess",
    ):
        click.echo(f">>> Mode [{mode}] not supported. Exit.\n")
        return

    if mode == "fingerprint":
        mode = "finger"

    if type:
        input_type = type.split(",")
    else:
        input_type = INPUT_TYPE
        if mode != "finger":
            input_type.remove("wsq")

    convert_type = convert.split(",") if convert else []
    target_type = target

    if mode == "filter":
        filter_job(input, columns, query, sort, cwd, prefix)
        return

    if mode == "report":
        report_job(input, cwd, prefix)
        return

    if mode == "preprocess":
        try:
            config = [i.casefold() for i in config.split(",")]
            configs = {"source": PROC_TYPE}

            for item in config:
                if item in PROC_TYPE:
                    configs["target"] = item
                try:
                    if 0 < (num := float(item)) <= 10:
                        configs["frac"] = num
                    else:
                        configs["width"] = int(num)
                except ValueError:
                    pass
            if "grayscale" in config or "greyscale" in config:
                configs["grayscale"] = True
            elif "rgb" in config:
                configs["rgb"] = True
            elif "rgba" in config:
                configs["rgba"] = True

            if not len(configs):
                click.echo(
                    f">>> Failed to parse configuration '{config}': no params found. Exit.\n"
                )
                return
        except Exception as e:
            click.echo(f">>> Failed to parse configuration '{config}': {e}. Exit.\n")
            return
        preprocess_job(input, output, debug, configs)
        return

    if not output:
        output = (Path(input) / str(int(time.time()))).as_posix()

    if benchmark:
        mode = "face" if not mode else mode
        asyncio.run(
            benchmark_job(
                mode,
                limit,
                engine,
                fusion,
                batch,
            )
        )
    elif mode:
        asyncio.run(
            assessment_job(
                mode,
                input,
                output,
                report,
                # log,
                limit,
                filename,
                input_type,
                convert_type,
                target_type,
                columns,
                query,
                sort,
                cwd,
                prefix,
                batch,
                fusion,
                engine,
                debug,
            )
        )


if __name__ == "__main__":
    main()
