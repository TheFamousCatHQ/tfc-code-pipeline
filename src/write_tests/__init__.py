#!/usr/bin/env python3
"""
Script to write unit tests for source files using aider.

This script finds source files in a specified directory using find-source-files
and then calls aider for each file with a message to write unit tests without using mocks.
"""

import argparse
import subprocess
import sys
from typing import List, Optional, Sequence

from find_source_files import find_source_files


def parse_args(args: Optional[Sequence[str]] = None) -> argparse.Namespace:
    """Parse command-line arguments.

    Args:
        args: Command line arguments. Defaults to None, which uses sys.argv.

    Returns:
        Parsed command-line arguments.
    """
    parser = argparse.ArgumentParser(
        description="Write unit tests for source files using aider"
    )
    parser.add_argument(
        "--directory",
        type=str,
        required=True,
        help="Directory to search for source files"
    )
    parser.add_argument(
        "--file",
        type=str,
        help="Specific file to process (optional, overrides directory search)"
    )
    parser.add_argument(
        "--message",
        type=str,
        default="write unit tests without using mocks for all functions found in this file. If tests already exist, check if they are up to date, if not update them to cover the current functionality.",
        help="Message to pass to aider (default: write unit tests without mocks)"
    )
    return parser.parse_args(args)


def write_tests_for_files(directory: str, specific_file: Optional[str] = None, message: str = "") -> List[str]:
    """Find source files and write tests for them using aider.

    Args:
        directory: Directory to search for source files.
        specific_file: Optional specific file to process.
        message: Message to pass to aider.

    Returns:
        List of files that were processed.
    """
    # If a specific file is provided, only process that file
    if specific_file:
        source_files = [specific_file]
    else:
        # Find source files in the directory
        source_files = find_source_files(directory)

    if not source_files:
        print(f"No source files found in directory: {directory}", file=sys.stderr)
        return []

    # Process each file with aider
    processed_files = []
    for file_path in source_files:
        print(f"Processing file: {file_path}")
        try:
            # Call aider with the file and message
            subprocess.run(
                ["aider", "--message", message, file_path],
                check=True,
                text=True,
            )
            processed_files.append(file_path)
        except subprocess.CalledProcessError as e:
            print(f"Error processing file {file_path}: {e}", file=sys.stderr)
        except FileNotFoundError:
            print("Error: 'aider' command not found. Please ensure it is installed.", file=sys.stderr)
            break

    return processed_files


def main() -> int:
    """Run the main script.

    Returns:
        Exit code (0 for success, non-zero for failure).
    """
    try:
        args = parse_args()
        processed_files = write_tests_for_files(args.directory, args.file, args.message)

        print(f"\nProcessed {len(processed_files)} files:")
        for file in processed_files:
            print(f"  - {file}")

        return 0
    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
