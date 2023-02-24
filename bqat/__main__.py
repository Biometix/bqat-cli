import click
from rich.console import Console
from rich.text import Text

from bqat import __name__ as name
from bqat import __version__ as version
from bqat.app import benchmark, run, filter
from bqat.utils import menu

INPUT_TYPE = ["wsq", "jpg", "jpeg", "png", "bmp", "jp2"]


@click.command()
@click.option(
    "--mode",
    "-M",
    default="",
    help="Specify assessment mode (Fingerprint, Face, Iris).",
)
@click.option(
    "--input",
    "-I",
    default="data/",
    help="Specify input directory."
)
@click.option(
    "--output",
    "-O",
    default="data/output/",
    help="Specify output directory."
)
# @click.option(
#     "--report",
#     "-R",
#     default="data/output/",
#     help="Specify report directory."
# )
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
    help="Run system benchmarking analysis."
)
@click.option(
    "--limit",
    "-L",
    type=int,
    default=0,
    help="Set a limit for number of files to scan."
)
@click.option(
    "--filename",
    "-F",
    default="*",
    help="Filename pattern to search within the input folder."
)
@click.option(
    "--search",
    "-S",
    default="",
    help="Specify file formats to search within the input folder."
)
@click.option(
    "--convert",
    "-C",
    default="",
    help="Specify file formats to convert before processing."
)
@click.option(
    "--target",
    "-T",
    default="",
    help="Specify target format to convert to."
)
@click.option(
    "--arm",
    "-A",
    is_flag=True,
    default=False,
    help="Disable multithreading (For ARM64 platform)."
)
@click.option(
    "--interactive",
    "-X",
    is_flag=True,
    default=False,
    help="Enter terminal interactive ui."
)
@click.option(
    "--attributes",
    "-D",
    default="",
    help="Specify attributes (columns) to investigate."
)
@click.option(
    "--query",
    "-Q",
    default="",
    help="Queries to apply on the attributes."
)
@click.option(
    "--sort",
    "-R",
    default="",
    help="Specify attributes (columns) to sort by."
)
@click.option(
    "--cwd",
    "-W",
    default="",
    help="Specify current working directory for url."
)
def main(
    input,
    output,
    # report,
    # log,
    benchmarking,
    mode,
    limit,
    filename,
    search,
    convert,
    target,
    arm,
    interactive,
    attributes,
    query,
    sort,
    cwd
):
    console = Console()
    title = Text("\nWelcome to")
    title.append(" ")
    title.append(name, style="bold dark_red")
    title.append(" ")
    title.append(f"v{version}\n", style="italic underline")
    console.print(title)

    if interactive:
        selections = menu()
        for k, v in selections.items():
            if k == "mode":
                mode = v
            if k == "benchmark":
                benchmarking = v
            if k == "input":
                input = v
            if k == "output":
                output = v
                # report = v    
                # log = v
            if k == "limit":
                limit = v
            if k == "filename":
                filename = v
            if k == "arm":
                arm = v
            if k == "search":
                search = v
            if k == "convert":
                convert = v
            if k == "target":
                target = v
        click.echo("")

    input_type = search.split() if search else INPUT_TYPE
    convert_type = convert.split()
    target_type = target

    mode = mode.casefold()
    if mode not in ("face", "finger", "fingerprint", "iris", "filter", ""):
        click.echo(f">>> Mode [{mode}] not supported, exit.")
        return
    if mode == "fingerprint": mode = "finger"

    if mode == "filter":
        filter(
            output,
            attributes,
            query,
            sort,
            cwd
        )
        return

    if benchmarking:
        mode = "face" if not mode else mode
        benchmark(mode, limit, arm)
    elif mode:
        run(
            mode,
            input,
            output,
            # report,
            # log,
            limit,
            filename,
            arm,
            input_type,
            convert_type,
            target_type,
            attributes,
            query,
            sort,
            cwd
        )      


if __name__ == "__main__":
    main()
