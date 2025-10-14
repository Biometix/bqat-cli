import argparse
import sys

from bqat.utils import handle_cli_update, handle_uninstall, run_container, show_version


def main() -> None:
    """Main execution function for the script."""
    parser = argparse.ArgumentParser(
        description="BQAT-CLI",
        add_help=False,  # We will pass --help to the container
    )
    parser.add_argument(
        "--version", "-v", action="store_true", help="Show version information."
    )
    parser.add_argument(
        "--update",
        action="store_true",
        help="Check for and apply updates to the Docker image.",
    )
    parser.add_argument(
        "--uninstall",
        action="store_true",
        help="Uninstall the CLI and remove the Docker image.",
    )

    args, unknown_args = parser.parse_known_args()

    if args.version:
        show_version()
    elif args.update:
        handle_cli_update()
    elif args.uninstall:
        handle_uninstall()
    else:
        # If no special commands are given, run the container with all args.
        # We pass the original, unprocessed arguments.
        all_args = sys.argv[1:]
        run_container(all_args)


if __name__ == "__main__":
    main()
