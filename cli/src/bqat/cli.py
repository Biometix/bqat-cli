import argparse

from bqat.utils import handle_cli_update, handle_uninstall, run_container, show_version

IMAGE_NAME = "ghcr.io/biometix/bqat-cli:latest"


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
        help="Check for and pull updates to the container image.",
    )
    parser.add_argument(
        "--uninstall",
        action="store_true",
        help="Uninstall the CLI and remove the container image.",
    )
    parser.add_argument(
        "--tag",
        help="Specify container image tag.",
    )

    args, unknown_args = parser.parse_known_args()

    if not args.tag:
        image_tag = IMAGE_NAME
    else:
        image_tag = args.tag

    if args.version:
        show_version(image_tag)
    elif args.update:
        handle_cli_update(image_tag)
    elif args.uninstall:
        handle_uninstall(image_tag)
    else:
        run_container(image_tag, unknown_args)


if __name__ == "__main__":
    main()
