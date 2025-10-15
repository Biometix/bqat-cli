import atexit
import json
import os
import platform
import re
import subprocess
import sys

from bqat import __package__, __version__


def get_total_memory_mb():
    """Get the total system memory in megabytes (MB)."""
    system = platform.system()
    try:
        if system == "Linux":
            result = subprocess.run(
                ["vmstat", "-s", "-S", "M"], capture_output=True, text=True, check=True
            )
            match = re.search(r"(\d+)\s+total memory", result.stdout)
            if match:
                return int(match.group(1))
        elif system == "Darwin":  # macOS
            result = subprocess.run(
                ["sysctl", "-n", "hw.memsize"],
                capture_output=True,
                text=True,
                check=True,
            )
            return int(result.stdout.strip()) // (1024 * 1024)
        elif system == "Windows":
            result = subprocess.run(
                ["wmic", "OS", "get", "TotalVisibleMemorySize", "/Value"],
                capture_output=True,
                text=True,
                check=True,
            )
            match = re.search(r"TotalVisibleMemorySize=(\d+)", result.stdout)
            if match:
                return int(match.group(1)) // 1024
    except (subprocess.CalledProcessError, FileNotFoundError, ValueError, TypeError):
        print("Warning: Could not determine total system memory.", file=sys.stderr)
    return 0


def get_shm_size(total_memory_mb):
    """Calculate the shared memory size (half of total memory) and format it."""
    if total_memory_mb > 0:
        shm_mb = total_memory_mb // 2
        return f"{shm_mb}MB"
    # Default to a safe size if memory could not be determined
    return "2048MB"


def check_update(image_tag) -> bool:
    """
    Checks if a newer version of the 'bqat-cli' Docker image is available.

    Returns:
        bool: True if an update is available, False otherwise.
    """
    try:
        # docker pull is smart enough to not download layers if the image is up to date.
        # It will only fetch new layers if the remote digest has changed.
        print("Checking for a newer version of the image...")
        pull_result = subprocess.run(
            ["docker", "pull", image_tag], capture_output=True, text=True, check=True
        )

        # If the output contains "Status: Image is up to date", no update was needed.
        # Otherwise, new layers were downloaded, meaning an update was available.
        return "Image is up to date" not in pull_result.stdout

    except (
        subprocess.CalledProcessError,
        FileNotFoundError,
    ):
        # If docker pull fails, it could be because the image doesn't exist locally yet,
        # or Docker isn't running. In either case, we can consider an "update" (initial pull)
        # to be available.
        return True


def handle_update(image_tag):
    """Handles the Docker update/pull logic."""
    print("Pulling the latest 'bqat-cli' image...")
    try:
        # Pull the image
        subprocess.run(
            ["docker", "pull", f"{image_tag}:latest"],
            check=True,
            capture_output=True,
            text=True,
        )

        # Inspect to show the version
        print("\nImage version information:")
        result = subprocess.run(
            ["docker", "inspect", "bqat-cli:latest"],
            capture_output=True,
            text=True,
            check=True,
        )
        image_info = json.loads(result.stdout)
        version = (
            image_info[0]
            .get("Config", {})
            .get("Labels", {})
            .get("image.version", "not found")
        )
        print(f'  "image.version": "{version}"')
    except subprocess.CalledProcessError as e:
        print(
            f"Error during Docker pull or inspect: {e.stderr.strip()}",
            file=sys.stderr,
        )
    except FileNotFoundError:
        print(
            "Error: 'docker' command not found. Ensure Docker is installed and in your PATH.",
            file=sys.stderr,
        )


def delete_image(image_tag):
    """Removes the 'bqat-cli:latest' Docker image."""
    print(f"Attempting to remove the '{image_tag}' Docker image...")
    try:
        subprocess.run(
            ["docker", "rmi", image_tag], check=True, capture_output=True, text=True
        )
        print(f"Successfully removed image '{image_tag}'.")
    except subprocess.CalledProcessError as e:
        error_message = e.stderr.decode().strip()
        if "No such image" in error_message:
            print(f"Image '{image_tag}' not found locally.")
        else:
            print(f"Error removing Docker image: {error_message}", file=sys.stderr)
            print(
                "This might be because a container is currently using the image.",
                file=sys.stderr,
            )
    except FileNotFoundError:
        print(
            "Error: 'docker' command not found. Ensure Docker is installed and in your PATH.",
            file=sys.stderr,
        )


def _uninstall_package():
    """Function to be called on exit to uninstall the package."""
    try:
        print("Uninstalling 'bqat-cli' package...")
        # Use subprocess.run and check for errors
        subprocess.run(
            [sys.executable, "-m", "pip", "uninstall", "-y", __package__],
            check=True,
            capture_output=True,
            text=True,
        )
        print(f"Successfully uninstalled '{__package__}'.")
    except subprocess.CalledProcessError as e:
        print(f"Failed to uninstall '{__package__}': {e.stderr}", file=sys.stderr)


def handle_uninstall(image_tag):
    """Handles the uninstall process."""
    try:
        confirm = input(f"Are you sure you want to uninstall {__package__}? (y/N): ")

        if confirm.lower() not in ("y", "yes"):
            print("Aborted")
            return

        print("Starting uninstall process...")

        # Remove container image
        confirm = input(
            f"Are you sure you want to remove the container image {image_tag} as well? (y/N): "
        )

        if confirm.lower() in ("y", "yes"):
            delete_image()

        # Register the uninstall function to run when this script exits.
        # This avoids issues with the script trying to delete itself while running.
        atexit.register(_uninstall_package)
    except (KeyboardInterrupt, EOFError):
        print("\nAborted")


def handle_cli_update(image_tag):
    """Handles the update check and process."""
    print("Checking for updates...")
    if check_update(image_tag):
        print("A new version is available or the image is not present locally.")
        handle_update(image_tag)
    else:
        print("Your 'bqat-cli' image is up to date.")


def show_version(image_tag):
    """Displays the version of the CLI and the container image."""
    # Version of the CLI app
    print(f"{__package__.upper()}: v{__version__}")
    # Version of the container image
    try:
        result = subprocess.run(
            ["docker", "inspect", image_tag],
            capture_output=True,
            text=True,
            check=True,
        )
        image_info = json.loads(result.stdout)
        image_version = (
            image_info[0]
            .get("Config", {})
            .get("Labels", {})
            .get("org.opencontainers.image.version", "not found")
        )
        print(f"BQAT-Core: {image_version}")
    except (
        subprocess.CalledProcessError,
        FileNotFoundError,
        json.JSONDecodeError,
        IndexError,
    ):
        print(
            f"Container image version: Could not determine (image '{image_tag}' not found or Docker not running).",
            file=sys.stderr,
        )


def run_container(image_tag, bqat_args: list[str]):
    """Builds and executes the docker run command."""
    current_dir = os.getcwd()
    data_dir = os.path.join(current_dir, "data")

    # Create 'data' directory if it doesn't exist (equivalent to [ ! -d data ] && mkdir data)
    if not os.path.isdir(data_dir):
        os.makedirs(data_dir)

    # Calculate SHM size
    total_mem = get_total_memory_mb()
    shm_size = get_shm_size(total_mem)

    # Build the base docker command
    docker_cmd = ["docker", "run", "--rm", "-it", f"--shm-size={shm_size}"]

    # Set the volume path based on the OS
    current_os = platform.system()
    if current_os in ("Linux", "Darwin"):
        volume_path = f"{current_dir}/data:/app/data"
    elif current_os == "Windows":
        volume_path = f"{data_dir}:/app/data"
    else:
        print(f"Error. Unidentified Host OS: {current_os}.", file=sys.stderr)
        sys.exit(1)

    docker_cmd.extend(["-v", volume_path])
    docker_cmd.append(image_tag)

    # The command to run inside the container
    if not bqat_args:
        show_version(image_tag)
        print()
        inner_command = ["python3 -m bqat --help"]
    else:
        inner_command = [f"python3 -m bqat -W {current_dir} {' '.join(bqat_args)}"]
    docker_cmd.extend(inner_command)

    try:
        subprocess.run(docker_cmd, check=True)
    except FileNotFoundError:
        print(
            "Error: 'docker' command not found. Ensure Docker is installed and in your PATH.",
            file=sys.stderr,
        )
        sys.exit(1)
    except subprocess.CalledProcessError as e:
        # The subprocess will have already printed its stderr.
        # We exit with the same return code as the docker command.
        sys.exit(e.returncode)
