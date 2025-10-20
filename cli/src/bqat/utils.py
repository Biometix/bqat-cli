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
    return "8192MB"


def get_digest_from_cli(command):
    """
    Executes a Docker CLI command and extracts the image digest.

    :param command: The full command as a list (e.g., ['docker', 'manifest', 'inspect', 'image:tag']).
    :return: The image digest (SHA-256 hash) as a string, or None if not found/error.
    """
    try:
        # Run the command and capture the output
        result = subprocess.run(command, capture_output=True, text=True, check=True)

        # The output is a JSON string
        manifest_data = json.loads(result.stdout)

        # The digest is usually stored in the 'Descriptor' key for 'docker manifest inspect'
        # or the first element of 'RepoDigests' for a local 'docker inspect'.

        # Check for remote manifest digest
        if isinstance(manifest_data, dict) and "Descriptor" in manifest_data:
            return manifest_data["Descriptor"]["digest"]

        # Check for local image digest (which is often returned as a list of repo digests)
        elif (
            isinstance(manifest_data, list)
            and manifest_data
            and "RepoDigests" in manifest_data[0]
        ):
            # Expecting a list of digests in the format 'repo@sha256:...'
            repo_digests = manifest_data[0]["RepoDigests"]
            if repo_digests:
                # Return the part after '@' for the first digest
                return repo_digests[0].split("@")[-1]

        # Handle the raw manifest digest if it's the only thing returned
        # This handles cases where docker manifest inspect returns a list of manifests for multi-arch images
        elif (
            isinstance(manifest_data, list)
            and manifest_data
            and "digest" in manifest_data[0]
        ):
            # For a multi-arch manifest list, we take the digest of the list itself
            return manifest_data[0].get(
                "digest"
            )  # This is less precise but safer for general use

        # Final fallback if parsing is tricky:
        if isinstance(manifest_data, dict) and "digest" in manifest_data.get(
            "config", {}
        ):
            return manifest_data["config"]["digest"]

    except subprocess.CalledProcessError as e:
        # Handles errors like "No such image" or "manifest unknown"
        if "No such image" in e.stderr or "manifest unknown" in e.stderr:
            return None
        print(f"Error executing command: {' '.join(command)}\n{e.stderr.strip()}")
        return None
    except json.JSONDecodeError:
        print("Error: Failed to parse JSON output from Docker CLI.")
        return None
    except Exception as e:
        print(f"An unexpected error occurred: {e}")
        return None


def check_update(image_tag) -> bool:
    """
    Checks if a newer version of the 'bqat-cli' Docker image is available.

    Returns:
        bool: True if an update is available, False otherwise.
    """
    try:
        # 1. Get Local Image Digest
        # We use `docker inspect` with a format filter to get JSON containing RepoDigests
        local_command = ["docker", "inspect", image_tag, "--format", "json"]
        local_digest = get_digest_from_cli(local_command)

        # 2. Get Remote Image Digest (without pulling)
        # We use `docker manifest inspect` to query the registry directly
        remote_command = ["docker", "manifest", "inspect", image_tag]
        remote_digest = get_digest_from_cli(remote_command)

        print(f"Local Digest:  {local_digest or 'N/A'}")
        print(f"Remote Digest: {remote_digest or 'N/A'}")

        # 3. Compare Digests
        if local_digest is None and remote_digest is None:
            print(
                "🛑 Neither local image nor remote manifest could be retrieved. Cannot determine status."
            )
            return True  # No image, so consider an "update" (initial pull) to be available.
        elif local_digest is None and remote_digest:
            print(
                "✅ Image not found locally, but remote version exists. **New image available** (or needs initial pull)."
            )
            return True  # No image, so consider an "update" (initial pull) to be available.
        elif local_digest and remote_digest is None:
            print(
                "⚠️ Local image exists, but remote manifest check failed (e.g., image deleted, auth issue). Status uncertain."
            )
            return False
        elif local_digest == remote_digest:
            print("👍 The local image is **UP-TO-DATE** with the remote registry.")
            return False
        elif local_digest != remote_digest:
            print("🚨 A **NEW** version of the image is available in the registry!")
            return True

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
            ["docker", "pull", f"{image_tag}"],
            check=True,
        )

        # Inspect to show the version
        print("\nImage version information:")
        result = subprocess.run(
            ["docker", "inspect", f"{image_tag}"],
            capture_output=True,
            text=True,
            check=True,
        )
        image_info = json.loads(result.stdout)
        labels = image_info[0].get("Config", {}).get("Labels", {})
        image_version = labels.get("bqat.cli.version", "not found")
        core_version = labels.get("bqat.core.version", "not found")

        print(f'  "bqat.cli.version": "{image_version}"')
        print(f'  "bqat.core.version": "{core_version}"')
    except subprocess.CalledProcessError as e:
        error_output = (
            e.stderr.strip() if e.stderr else "See the output above for details."
        )
        print(
            f"Error during Docker operation: {error_output}",
            file=sys.stderr,
        )
    except FileNotFoundError:
        print(
            "Error: 'docker' command not found. Ensure Docker is installed and in your PATH.",
            file=sys.stderr,
        )
    except (json.JSONDecodeError, IndexError) as e:
        print(f"Error parsing Docker image information: {e}", file=sys.stderr)


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
        if "python" not in sys.executable:
            print(
                "You are probably running via EXE instead of PyPI package, no need to uninstall."
            )
        else:
            subprocess.run(
                [sys.executable, "-m", "pip", "uninstall", "-y", __package__],
                check=True,
            )
    except subprocess.CalledProcessError as e:
        print(f"Failed to uninstall '{__package__}': {str(e)}", file=sys.stderr)


def handle_uninstall(image_tag):
    """Handles the uninstall process."""
    try:
        confirm = input(f"Are you sure you want to uninstall {__package__}? (y/N): ")

        if confirm.lower() not in ("y", "yes"):
            print("Aborted")
            return

        # Remove container image
        confirm = input(
            f"Are you sure you want to remove the container {image_tag} too? (y/N): "
        )

        print("Starting uninstall process...")

        if confirm.lower() in ("y", "yes"):
            delete_image(image_tag)

        # Register the uninstall function to run when this script exits.
        # This avoids issues with the script trying to delete itself while running.
        atexit.register(_uninstall_package)
    except (KeyboardInterrupt, EOFError):
        print("\nAborted")


def handle_cli_update(image_tag):
    """Handles the update check and process."""
    print(f'Checking for updates to "{image_tag}"...')
    if check_update(image_tag):
        confirm = input("> Do you want to pull the latest? (y/N): ")
        if confirm.lower() in ("y", "yes"):
            handle_update(image_tag)
    else:
        print(f"Your '{image_tag}' image is up to date.")


def show_version(image_tag):
    """Displays the version of the CLI and the container image."""
    # Version of the CLI app
    print(f"BQAT CLI: v{__version__}")
    # Version of the container image
    try:
        result = subprocess.run(
            ["docker", "inspect", image_tag],
            capture_output=True,
            text=True,
            check=True,
        )
        image_info = json.loads(result.stdout)
        core_version = (
            image_info[0]
            .get("Config", {})
            .get("Labels", {})
            .get("bqat.core.version", "not found")
        )
        image_version = (
            image_info[0]
            .get("Config", {})
            .get("Labels", {})
            .get("bqat.cli.version", "not found")
        )
        print(f"BQAT Core: {core_version}")
        print(f"Container image: {image_version}")
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
