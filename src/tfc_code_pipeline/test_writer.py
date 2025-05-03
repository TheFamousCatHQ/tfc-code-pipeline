#!/usr/bin/env python3
"""
Script to write unit tests for tokenUtils.js using aider.

This script is a specialized version of write_tests that specifically targets
tokenUtils.js and provides a custom prompt for aider.
"""

import argparse
import os
import subprocess
import sys
from pathlib import Path
from typing import Optional, Sequence

from logging_utils import get_logger

# Set up logging
logger = get_logger()


def parse_args(args: Optional[Sequence[str]] = None) -> argparse.Namespace:
    """Parse command-line arguments.

    Args:
        args: Command line arguments. Defaults to None, which uses sys.argv.

    Returns:
        Parsed command-line arguments.
    """
    parser = argparse.ArgumentParser(
        description="Write unit tests for tokenUtils.js using aider"
    )
    parser.add_argument(
        "--directory",
        type=str,
        required=True,
        help="Directory containing tokenUtils.js"
    )
    return parser.parse_args(args)


def find_token_utils_file(directory: str) -> Optional[str]:
    """Find tokenUtils.js in the specified directory.

    Args:
        directory: Directory to search for tokenUtils.js.

    Returns:
        Path to tokenUtils.js if found, None otherwise.
    """
    dir_path = Path(directory).resolve()

    if not dir_path.exists():
        logger.error(f"Error: Directory '{directory}' does not exist.")
        return None

    if not dir_path.is_dir():
        logger.error(f"Error: '{directory}' is not a directory.")
        return None

    # Search for tokenUtils.js in the directory and its subdirectories
    for root, _, files in os.walk(dir_path):
        for file in files:
            if file.lower() == "tokenutils.js":
                return str(Path(root) / file)

    logger.error(f"Error: tokenUtils.js not found in directory: {directory}")
    return None


def write_tests_for_token_utils(file_path: str) -> bool:
    """Write unit tests for tokenUtils.js using aider.

    Args:
        file_path: Path to tokenUtils.js.

    Returns:
        True if successful, False otherwise.
    """
    # Custom message for aider
    message = (
        "write unit tests without using mocks for all functions found in tokenUtils.js. "
        "If tests already exists, check if their are up to date, if not update them to cover the current functionality."
    )

    logger.info(f"Processing file: {file_path}")
    try:
        # Call aider with the file and message
        subprocess.run(
            ["aider", "--message", message, file_path],
            check=True,
            text=True,
        )
        return True
    except subprocess.CalledProcessError as e:
        logger.error(f"Error processing file {file_path}: {e}")
        return False
    except FileNotFoundError:
        logger.error("Error: 'aider' command not found. Please ensure it is installed.")
        return False


def main() -> int:
    """Run the main script.

    Returns:
        Exit code (0 for success, non-zero for failure).
    """
    try:
        args = parse_args()

        # Find tokenUtils.js
        file_path = find_token_utils_file(args.directory)
        if not file_path:
            return 1

        # Write tests for tokenUtils.js
        success = write_tests_for_token_utils(file_path)

        if success:
            logger.info(f"Successfully processed: {file_path}")
            return 0
        else:
            return 1
    except Exception as e:
        logger.error(f"Error: {e}")
        return 1


if __name__ == "__main__":
    sys.exit(main())
