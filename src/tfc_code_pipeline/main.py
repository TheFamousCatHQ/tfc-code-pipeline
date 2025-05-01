"""Main module for TFC Code Pipeline.

This module provides the main functionality for the TFC Code Pipeline,
including Docker container creation and environment variable handling.
"""

import logging
import os
import subprocess
import sys
from pathlib import Path
from typing import Dict, List, Optional, Union, Sequence

# Set up logging
logger = logging.getLogger(__name__)

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
        logger.warning("python-dotenv package not installed. Environment variables from .env file will not be loaded.")
        return False


def read_env_file(env_file_path: Union[str, Path]) -> Dict[str, str]:
    """Read environment variables from a .env file.

    Args:
        env_file_path: Path to the .env file.

    Returns:
        Dict[str, str]: Dictionary of environment variables from the .env file.
    """
    env_vars = {}

    try:
        with open(env_file_path, 'r') as f:
            for line in f:
                line = line.strip()
                if not line or line.startswith('#'):
                    continue

                key, value = line.split('=', 1)
                env_vars[key] = value

        return env_vars
    except Exception as e:
        logger.error(f"Error reading .env file: {e}")
        return {}


def format_docker_cmd(docker_cmd: Sequence[str]) -> str:
    """Format a Docker command list as a string for logging.

    Args:
        docker_cmd: The Docker command as a list of strings.

    Returns:
        A formatted string representation of the Docker command.
    """
    # Create a copy of the command to avoid modifying the original
    cmd_copy = list(docker_cmd)

    # Replace environment variables with a placeholder to make the output more readable
    i = 0
    while i < len(cmd_copy) - 1:
        if cmd_copy[i] == "-e" and "=" in cmd_copy[i+1]:
            # Keep only the first few and last few environment variables
            if i > 120:  # If we have a lot of env vars, truncate them
                cmd_copy[i+1] = "...[env vars truncated]..."
                # Skip ahead to the next non-env var argument
                while i+2 < len(cmd_copy) and cmd_copy[i+2] == "-e":
                    cmd_copy.pop(i+2)  # Remove the next -e
                    if i+2 < len(cmd_copy):
                        cmd_copy.pop(i+2)  # Remove the corresponding value
        i += 1

    # Join the command with spaces
    return " ".join(cmd_copy)


def main(build_only: bool = False, run: bool = False, src: Optional[str] = None, cmd: str = "explain_code", processor_args: Optional[Dict[str, str]] = None) -> int:
    """Run the main application.

    Creates a one-shot Docker container based on Python 3.12,
    installs Aider and the explain-code script, and runs the specified command
    (either explain_code or write_tests) with the provided messages.
    Exposes all environment variables from .env file to the Docker container.
    Optionally mounts a source directory in the container under /src.

    Args:
        build_only: If True, only build the Docker image without running the container.
        run: If True, run the Docker container with the provided messages.
        src: Directory to mount in the Docker container under /src. Defaults to None.
        messages: Custom message to pass to aider. Defaults to "Hello".
        cmd: Command to run in the Docker container. Choices are "explain_code" or "write_tests". Defaults to "explain_code".
        processor_args: Dictionary of processor-specific arguments to pass to the Docker container. Defaults to None.

    Returns:
        Exit code (0 for success, non-zero for failure).
    """
    # Initialize processor_args if None
    if processor_args is None:
        processor_args = {}
    # Define constants
    IMAGE_NAME = "tfc-code-pipeline:python3.12"
    DOCKERFILE_CONTENT = """\
FROM python:3.12-slim

# Install aider-chat and our package
RUN pip install --no-cache-dir aider-chat
COPY . /app
WORKDIR /app
RUN pip install --no-cache-dir -e .

# Entrypoint will be set when running the container
ENTRYPOINT ["/bin/bash"]
"""

    # Configure logging
    configure_logging()

    if build_only:
        logger.info(f"TFC Code Pipeline - Building Docker image: {IMAGE_NAME}...")
    elif run:
        logger.info(f"TFC Code Pipeline - Running {cmd} in Docker container...")
    else:
        logger.info(f"TFC Code Pipeline - Starting {cmd} in Docker container...")

    try:
        # Load environment variables from .env file
        env_file = Path(".env")
        if env_file.exists():
            logger.info("Loading environment variables from .env file...")
            load_dotenv(env_file)
            # Get only environment variables from .env file
            env_vars: Dict[str, str] = read_env_file(env_file)
        else:
            logger.info("No .env file found. No environment variables will be passed to Docker.")
            env_vars = {}

        if build_only:
            # Create a Dockerfile
            dockerfile_path = Path("Dockerfile")
            with open(dockerfile_path, "w") as f:
                f.write(DOCKERFILE_CONTENT)

            # Build the Docker image
            logger.info(f"Building Docker image: {IMAGE_NAME}")
            build_cmd: List[str] = ["docker", "build", "-t", IMAGE_NAME, "."]
            result = subprocess.run(build_cmd, check=True)

            # Remove the temporary Dockerfile
            dockerfile_path.unlink()

            logger.info(f"Docker image built successfully: {IMAGE_NAME}")
            logger.info(
                f"You can now run it with: docker run --rm -it -v /path/to/source:/src --entrypoint explain-code {IMAGE_NAME} --directory \"/src\" --message \"Your message\"")
            logger.info(
                f"Or use write-tests: docker run --rm -it -v /path/to/source:/src --entrypoint write-tests {IMAGE_NAME} --directory \"/src\"")

            return result.returncode
        elif run:
            # Create a Dockerfile if it doesn't exist
            dockerfile_path = Path("Dockerfile")
            if not dockerfile_path.exists():
                with open(dockerfile_path, "w") as f:
                    f.write(DOCKERFILE_CONTENT)

                # Build the Docker image
                logger.info(f"Building Docker image: {IMAGE_NAME}")
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
                    logger.error(f"Error: Source directory '{src}' does not exist.")
                    return 1
                if not src_path.is_dir():
                    logger.error(f"Error: '{src}' is not a directory.")
                    return 1
                logger.info(f"Mounting source directory: {src_path} -> /src")
                docker_cmd.extend(["-v", f"{src_path}:/src"])

            # Process output argument before adding the image name
            script_args = ["--directory", "/src"]
            for arg_name, arg_value in processor_args.items():
                if arg_name == "output":
                    # Mount the output file's directory as a volume in the Docker container
                    output_path = Path(arg_value)
                    output_dir = output_path.parent
                    output_filename = output_path.name
                    docker_output_path = f"/output/{output_filename}"

                    # Create the output directory if it doesn't exist
                    output_dir.mkdir(parents=True, exist_ok=True)

                    # Add the volume mount for the output directory (Docker argument)
                    docker_cmd.extend(["-v", f"{output_dir}:/output"])

                    # Add the output path argument for the script (script argument)
                    script_args.extend(["-o", docker_output_path])

            # Add the image and command
            docker_cmd.extend([
                "--entrypoint", cmd.replace("_", "-"),
                IMAGE_NAME
            ])

            # Add script arguments
            docker_cmd.extend(script_args)

            # Run the Docker command
            logger.info(f"Running {cmd} in Docker container")
            logger.debug(f"Docker command: {format_docker_cmd(docker_cmd)}")
            result = subprocess.run(docker_cmd, check=True)
            return result.returncode
        else:
            # Create a Dockerfile
            dockerfile_path = Path("Dockerfile")
            with open(dockerfile_path, "w") as f:
                f.write(DOCKERFILE_CONTENT)

            # Build the Docker image if it doesn't exist
            logger.info(f"Building Docker image: {IMAGE_NAME}")
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
                    logger.error(f"Error: Source directory '{src}' does not exist.")
                    return 1
                if not src_path.is_dir():
                    logger.error(f"Error: '{src}' is not a directory.")
                    return 1
                logger.info(f"Mounting source directory: {src_path} -> /src")
                docker_cmd.extend(["-v", f"{src_path}:/src"])

            # Process output argument before adding the image name
            script_args = ["--directory", "/src"]
            for arg_name, arg_value in processor_args.items():
                if arg_name == "output":
                    # Mount the output file's directory as a volume in the Docker container
                    output_path = Path(arg_value)
                    output_dir = output_path.parent
                    output_filename = output_path.name
                    docker_output_path = f"/output/{output_filename}"

                    # Create the output directory if it doesn't exist
                    output_dir.mkdir(parents=True, exist_ok=True)

                    # Add the volume mount for the output directory (Docker argument)
                    docker_cmd.extend(["-v", f"{output_dir}:/output"])

                    # Add the output path argument for the script (script argument)
                    script_args.extend(["-o", docker_output_path])

            # Add the image and command
            docker_cmd.extend([
                "--entrypoint", cmd.replace("_", "-"),
                IMAGE_NAME
            ])

            # Add script arguments
            docker_cmd.extend(script_args)

            # Run the Docker command
            logger.info(f"Running {cmd} in Docker container")
            logger.debug(f"Docker command: {format_docker_cmd(docker_cmd)}")
            result = subprocess.run(docker_cmd, check=True)
            return result.returncode

    except subprocess.CalledProcessError as e:
        logger.error(f"Error running Docker command: {e}")
        return e.returncode
    except FileNotFoundError:
        logger.error("Error: Docker not found. Please make sure Docker is installed and in your PATH.")
        return 1
    except Exception as e:
        logger.error(f"Unexpected error: {e}")
        return 1


def configure_logging(verbose: bool = False):
    """Configure logging for the TFC Code Pipeline.

    Args:
        verbose: Whether to enable verbose (DEBUG) logging.
    """
    # Set up root logger
    root_logger = logging.getLogger()

    # Remove existing handlers
    for handler in root_logger.handlers[:]:
        root_logger.removeHandler(handler)

    # Create console handler
    console = logging.StreamHandler()

    # Set format
    formatter = logging.Formatter('%(levelname)s - %(name)s - %(message)s')
    console.setFormatter(formatter)

    # Add handler to root logger
    root_logger.addHandler(console)

    # Set level based on verbose flag
    if verbose:
        root_logger.setLevel(logging.DEBUG)
        logger.debug("Verbose logging enabled")
    else:
        root_logger.setLevel(logging.INFO)


if __name__ == "__main__":
    exit(main())
