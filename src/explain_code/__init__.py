#!/usr/bin/env python3
"""
Script to explain code in source files using aider.

This script finds source files in a specified directory using find-source-files
and then calls aider for each file with the message "explain this code".
"""

import argparse
import subprocess
import sys
from typing import List, Optional, Sequence

from src.find_source_files import find_source_files


def parse_args(args: Optional[Sequence[str]] = None) -> argparse.Namespace:
    """Parse command-line arguments.

    Args:
        args: Command line arguments. Defaults to None, which uses sys.argv.

    Returns:
        Parsed command-line arguments.
    """
    parser = argparse.ArgumentParser(
        description="Explain code in source files using aider"
    )
    parser.add_argument(
        "--directory",
        type=str,
        required=True,
        help="Directory to search for source files"
    )
    parser.add_argument(
        "--message",
        type=str,
        default="explain this code",
        help="Message to pass to aider (default: 'explain this code')"
    )
    return parser.parse_args(args)


def explain_files(directory: str, message: str) -> List[str]:
    """Find source files and explain them using aider.

    Args:
        directory: Directory to search for source files.
        message: Message to pass to aider.

    Returns:
        List of files that were processed.
    """
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
        processed_files = explain_files(args.directory, args.message)
        
        print(f"\nProcessed {len(processed_files)} files:")
        for file in processed_files:
            print(f"  - {file}")
        
        return 0
    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())