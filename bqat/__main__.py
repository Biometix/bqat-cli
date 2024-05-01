import click
from rich.console import Console
from rich.text import Text

from bqat import __name__ as name
from bqat import __version__ as version
from bqat.app import benchmark, filter, preprocess, report, run

# from bqat.utils import menu

INPUT_TYPE = ["wsq", "jpg", "jpeg", "png", "bmp", "jp2"]


@click.command()
@click.option(
    "--mode",
    "-M",
    default="",
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
    "--reporting",
    "-R",
    default="true",
    help="Enable reporting.",
)
# @click.option(
#     "--log",
#     "-L",
#     default="data/output/",
#     help="Specify log directory.")
@click.option(
    "--benchmarking",
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
@click.option(
    "--arm",
    "-A",
    is_flag=True,
    default=False,
    help="Disable multithreading (For ARM64 platform).",
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
    "--engine",
    "-E",
    default="bqat",
    help="Specify alternative face processing engine (BQAT, OFIQ, BIQT).",
)
@click.option(
    "--config",
    default="",
    help='Configure preprocessing task ("[target format],[target width],[color mode (grayscale, rgb)]").',
)
@click.option(
    "--debugging",
    default="false",
    help="Enable debugging mode (print out runtime logs).",
)
def main(
    input,
    output,
    reporting,
    # log,
    benchmarking,
    mode,
    limit,
    filename,
    type,
    convert,
    target,
    arm,
    # interactive,
    columns,
    query,
    sort,
    cwd,
    engine,
    config,
    debugging,
):
    console = Console()
    title = Text("\nWelcome to")
    title.append(" ")
    title.append(name, style="bold dark_red")
    title.append(" ")
    title.append(f"v{version}\n", style="italic underline")
    console.print(title)

    if reporting in ("true", "True", "Yes", "yes"):
        reporting = True
    elif reporting in ("false", "False", "No", "no"):
        reporting = False
    else:
        reporting = True

    if debugging in ("true", "True", "Yes", "yes"):
        debugging = True
    elif debugging in ("false", "False", "No", "no"):
        debugging = False
    else:
        debugging = True

    if query and columns:
        if not len([True for col in columns.split(",") if col in query]):
            click.echo(
                f'>>> Query ("{query}") invalid for selected columns ({columns.split(",")}). Exit.\n'
            )
            return

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
        filter(input, columns, query, sort, cwd)
        return

    if mode == "report":
        report(input, cwd)
        return

    if mode == "preprocess":
        try:
            config = [i.casefold() for i in config.split(",")]
            configs = {}

            for item in config:
                if item in INPUT_TYPE:
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
        preprocess(input, output, debugging, configs)
        return

    if not output:
        output = "data/output/"

    if benchmarking:
        mode = "face" if not mode else mode
        benchmark(mode, limit, arm, engine)
    elif mode:
        run(
            mode,
            input,
            output,
            reporting,
            # log,
            limit,
            filename,
            arm,
            input_type,
            convert_type,
            target_type,
            columns,
            query,
            sort,
            cwd,
            engine,
            debugging,
        )


if __name__ == "__main__":
    main()
