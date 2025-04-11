"""Main module for TFC Test Writer Aider.

This module provides the main functionality for the TFC Test Writer Aider,
including Docker container creation and environment variable handling.
"""

import os
import subprocess
import sys
from pathlib import Path
from typing import Dict, List, Optional, Union

# Third-party imports
try:
    from dotenv import load_dotenv
except ImportError:
    # Fallback if dotenv is not installed
    def load_dotenv(dotenv_path: Optional[Union[str, Path]] = None) -> bool:
        """Dummy function if dotenv is not installed.

        Args:
            dotenv_path: Path to the .env file. Defaults to None.

        Returns:
            bool: Always False as no environment variables are loaded.
        """
        print("Warning: python-dotenv package not installed. Environment variables from .env file will not be loaded.")
        return False


def main(build_only: bool = False, run: bool = False, messages: str = "Hello", src: Optional[str] = None) -> int:
    """Run the main application.

    Creates a one-shot Docker container based on Python 3.12,
    installs Aider and the explain-code script, and runs the command 
    'explain-code --directory "/src" --message "<messages>"'.
    Exposes all environment variables from .env file to the Docker container.
    Optionally mounts a source directory in the container under /src.

    Args:
        build_only: If True, only build the Docker image without running the container.
        run: If True, run the Docker container with the provided messages.
        messages: Messages to pass to the Docker container. Defaults to "Hello".
        src: Directory to mount in the Docker container under /src. Defaults to None.

    Returns:
        Exit code (0 for success, non-zero for failure).
    """
    # Define constants
    IMAGE_NAME = "tfc-test-writer-aider:python3.12"
    DOCKERFILE_CONTENT = """\
FROM python:3.12-slim

# Install aider-chat and our package
RUN pip install --no-cache-dir aider-chat
COPY . /app
WORKDIR /app
RUN pip install --no-cache-dir -e .

# Use explain-code script as entrypoint
ENTRYPOINT ["explain-code"]
"""

    if build_only:
        print(f"TFC Test Writer Aider - Building Docker image: {IMAGE_NAME}...")
    elif run:
        print(f"TFC Test Writer Aider - Running explain-code in Docker container with message: '{messages}'...")
    else:
        print("TFC Test Writer Aider - Starting explain-code in Docker container...")

    try:
        # Load environment variables from .env file
        env_file = Path(".env")
        if env_file.exists():
            print("Loading environment variables from .env file...")
            load_dotenv(env_file)
        else:
            print("No .env file found. Using system environment variables.")

        # Get all environment variables
        env_vars: Dict[str, str] = dict(os.environ)

        if build_only:
            # Create a Dockerfile
            dockerfile_path = Path("Dockerfile")
            with open(dockerfile_path, "w") as f:
                f.write(DOCKERFILE_CONTENT)

            # Build the Docker image
            print(f"Building Docker image: {IMAGE_NAME}")
            build_cmd: List[str] = ["docker", "build", "-t", IMAGE_NAME, "."]
            result = subprocess.run(build_cmd, check=True)

            # Remove the temporary Dockerfile
            dockerfile_path.unlink()

            print(f"Docker image built successfully: {IMAGE_NAME}")
            print(f"You can now run it with: docker run --rm -it -v /path/to/source:/src {IMAGE_NAME} --directory \"/src\" --message \"Your message\"")

            return result.returncode
        elif run:
            # Create a Dockerfile if it doesn't exist
            dockerfile_path = Path("Dockerfile")
            if not dockerfile_path.exists():
                with open(dockerfile_path, "w") as f:
                    f.write(DOCKERFILE_CONTENT)

                # Build the Docker image
                print(f"Building Docker image: {IMAGE_NAME}")
                build_cmd: List[str] = ["docker", "build", "-t", IMAGE_NAME, "."]
                subprocess.run(build_cmd, check=True)

            # Create Docker command with environment variables
            docker_cmd: List[str] = ["docker", "run", "--rm", "-it"]

            # Add each environment variable to the Docker command
            for key, value in env_vars.items():
                docker_cmd.extend(["-e", f"{key}={value}"])

            # Mount source directory if provided
            if src:
                src_path = Path(src).resolve()
                if not src_path.exists():
                    print(f"Error: Source directory '{src}' does not exist.", file=sys.stderr)
                    return 1
                if not src_path.is_dir():
                    print(f"Error: '{src}' is not a directory.", file=sys.stderr)
                    return 1
                print(f"Mounting source directory: {src_path} -> /src")
                docker_cmd.extend(["-v", f"{src_path}:/src"])

            # Add the image and command
            docker_cmd.extend([
                IMAGE_NAME,
                "--directory", "/src",
                "--message", messages
            ])

            # Run the Docker command
            print(f"Running explain-code in Docker container with message: '{messages}'")
            result = subprocess.run(docker_cmd, check=True)
            return result.returncode
        else:
            # Create a Dockerfile
            dockerfile_path = Path("Dockerfile")
            with open(dockerfile_path, "w") as f:
                f.write(DOCKERFILE_CONTENT)

            # Build the Docker image if it doesn't exist
            print(f"Building Docker image: {IMAGE_NAME}")
            build_cmd: List[str] = ["docker", "build", "-t", IMAGE_NAME, "."]
            subprocess.run(build_cmd, check=True)

            # Remove the temporary Dockerfile
            dockerfile_path.unlink()

            # Create Docker command with environment variables
            docker_cmd: List[str] = ["docker", "run", "--rm", "-it"]

            # Add each environment variable to the Docker command
            for key, value in env_vars.items():
                docker_cmd.extend(["-e", f"{key}={value}"])

            # Mount source directory if provided
            if src:
                src_path = Path(src).resolve()
                if not src_path.exists():
                    print(f"Error: Source directory '{src}' does not exist.", file=sys.stderr)
                    return 1
                if not src_path.is_dir():
                    print(f"Error: '{src}' is not a directory.", file=sys.stderr)
                    return 1
                print(f"Mounting source directory: {src_path} -> /src")
                docker_cmd.extend(["-v", f"{src_path}:/src"])

            # Add the image and command
            docker_cmd.extend([
                IMAGE_NAME,
                "--directory", "/src",
                "--message", "Hello"
            ])

            # Run the Docker command
            result = subprocess.run(docker_cmd, check=True)
            return result.returncode

    except subprocess.CalledProcessError as e:
        print(f"Error running Docker command: {e}", file=sys.stderr)
        return e.returncode
    except FileNotFoundError:
        print("Error: Docker not found. Please make sure Docker is installed and in your PATH.", file=sys.stderr)
        return 1
    except Exception as e:
        print(f"Unexpected error: {e}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    exit(main())
