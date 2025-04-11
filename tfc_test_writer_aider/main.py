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


def main(build_only: bool = False) -> int:
    """Run the main application.

    Creates a one-shot Docker container based on Python 3.12,
    installs Aider, and runs the command 'aider --message "Hello"'.
    Exposes all environment variables from .env file to the Docker container.

    Args:
        build_only: If True, only build the Docker image without running the container.

    Returns:
        Exit code (0 for success, non-zero for failure).
    """
    # Define constants
    IMAGE_NAME = "tfc-test-writer-aider:python3.12"
    DOCKERFILE_CONTENT = """\
FROM python:3.12-slim

RUN pip install --no-cache-dir aider-chat

ENTRYPOINT ["aider"]
"""

    if build_only:
        print(f"TFC Test Writer Aider - Building Docker image: {IMAGE_NAME}...")
    else:
        print("TFC Test Writer Aider - Starting Docker container...")

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
            # dockerfile_path.unlink()

            print(f"Docker image built successfully: {IMAGE_NAME}")
            print(f"You can now run it with: docker run --rm -it {IMAGE_NAME} --message \"Your message\"")

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
            # dockerfile_path.unlink()

            # Create Docker command with environment variables
            docker_cmd: List[str] = ["docker", "run", "--rm", "-it"]

            # Add each environment variable to the Docker command
            for key, value in env_vars.items():
                docker_cmd.extend(["-e", f"{key}={value}"])

            # Add the image and command
            docker_cmd.extend([
                IMAGE_NAME,
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
