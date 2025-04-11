#!/usr/bin/env python3
"""
Base module for processing code files using aider.

This module provides a base class for scripts that process code files using aider,
such as explaining code or writing tests.
"""

import argparse
import subprocess
import sys
from abc import ABC, abstractmethod
from typing import List, Optional, Sequence

from find_source_files import find_source_files


class CodeProcessor(ABC):
    """Base class for processing code files using aider."""

    @abstractmethod
    def get_default_message(self) -> str:
        """Get the default message to pass to aider.

        Returns:
            Default message for aider.
        """
        pass

    @abstractmethod
    def get_description(self) -> str:
        """Get the description for the argument parser.

        Returns:
            Description string.
        """
        pass

    def parse_args(self, args: Optional[Sequence[str]] = None) -> argparse.Namespace:
        """Parse command-line arguments.

        Args:
            args: Command line arguments. Defaults to None, which uses sys.argv.

        Returns:
            Parsed command-line arguments.
        """
        parser = argparse.ArgumentParser(
            description=self.get_description()
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
            default=self.get_default_message(),
            help=f"Message to pass to aider (default: '{self.get_default_message()}')"
        )
        return parser.parse_args(args)

    def process_files(self, directory: str, specific_file: Optional[str] = None, message: Optional[str] = None) -> List[str]:
        """Find source files and process them using aider.

        Args:
            directory: Directory to search for source files.
            specific_file: Optional specific file to process.
            message: Message to pass to aider. If None, uses the default message.

        Returns:
            List of files that were processed.
        """
        # Use default message if none provided
        if message is None:
            message = self.get_default_message()

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

    def run(self) -> int:
        """Run the code processor.

        Returns:
            Exit code (0 for success, non-zero for failure).
        """
        try:
            args = self.parse_args()
            processed_files = self.process_files(args.directory, args.file, args.message)

            print(f"\nProcessed {len(processed_files)} files:")
            for file in processed_files:
                print(f"  - {file}")

            return 0
        except Exception as e:
            print(f"Error: {e}", file=sys.stderr)
            return 1
