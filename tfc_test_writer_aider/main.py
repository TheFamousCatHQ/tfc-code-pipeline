"""Main module for TFC Test Writer Aider."""

import os
import subprocess
import sys
from pathlib import Path
try:
    from dotenv import load_dotenv
except ImportError:
    # Fallback if dotenv is not installed
    def load_dotenv(dotenv_path=None):
        """Dummy function if dotenv is not installed."""
        print("Warning: python-dotenv package not installed. Environment variables from .env file will not be loaded.")
        return False


def main(build_only=False):
    """Run the main application.

    Creates a one-shot Docker container based on Python 3.12,
    installs Aider, and runs the command 'aider --message "Hello"'.
    Exposes all environment variables from .env file to the Docker container.

    Args:
        build_only (bool): If True, only build the Docker image without running the container.

    Returns:
        int: Exit code (0 for success, non-zero for failure)
    """
    # Define the Docker image name
    image_name = "tfc-test-writer-aider:python3.12"

    if build_only:
        print(f"TFC Test Writer Aider - Building Docker image: {image_name}...")
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
        env_vars = os.environ

        if build_only:
            # Create a Dockerfile
            dockerfile_content = """\
FROM python:3.12-slim

RUN pip install --no-cache-dir aider-chat

ENTRYPOINT ["aider"]
"""
            dockerfile_path = Path("Dockerfile")
            with open(dockerfile_path, "w") as f:
                f.write(dockerfile_content)

            # Build the Docker image
            print(f"Building Docker image: {image_name}")
            build_cmd = ["docker", "build", "-t", image_name, "."]
            result = subprocess.run(build_cmd, check=True)

            # Remove the temporary Dockerfile
            dockerfile_path.unlink()

            print(f"Docker image built successfully: {image_name}")
            print(f"You can now run it with: docker run --rm -it {image_name} --message \"Your message\"")

            return result.returncode
        else:
            # Create Docker command with environment variables
            docker_cmd = ["docker", "run", "--rm", "-it"]

            # Add each environment variable to the Docker command
            for key, value in env_vars.items():
                docker_cmd.extend(["-e", f"{key}={value}"])

            # Add the image and command
            docker_cmd.extend([
                "python:3.12-slim",
                "bash", "-c",
                "pip install aider-chat && aider --message \"Hello\""
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
