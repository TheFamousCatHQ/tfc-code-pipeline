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

from find_source_files import find_source_files as find_files


class CodeProcessor(ABC):
    """Base class for processing code files using aider."""

    # --- Configuration Properties (Subclasses can override) ---

    operates_on_whole_codebase: bool = False
    """Whether this processor operates on the whole codebase at once (True)
       or on a file-by-file basis (False)."""

    # --- Abstract Methods (Subclasses must implement) ---

    @abstractmethod
    def get_default_message(self) -> str:
        """Get the default message to pass to aider.

        Returns:
            Default message for aider.
        """
        return "/ask what does this code do?"

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

    # --- Core Processing Logic ---

    def _run_aider(self, files: List[str], message: str) -> bool:
        """Run aider with the specified files and message.

        Args:
            files: List of file paths to pass to aider.
            message: Message to pass to aider.

        Returns:
            True if aider ran successfully, False otherwise.
        """
        command = ["aider", "--message", message] + files
        print(f"Running command: {' '.join(command)}")  # For debugging
        try:
            subprocess.run(
                command,
                check=True,
                text=True,
                # Consider adding capture_output=True if subclasses need output
            )
            return True
        except subprocess.CalledProcessError as e:
            file_list = ', '.join(files)
            print(f"Error processing file(s) {file_list}: {e}", file=sys.stderr)
            return False
        except FileNotFoundError:
            # This error is critical, stop the process.
            print(
                "Error: 'aider' command not found. Please ensure it is installed and in your PATH.",
                file=sys.stderr,
            )
            raise  # Re-raise to stop execution in run()

    def process_files(
            self,
            directory: str,
            specific_file: Optional[str] = None,
            message: Optional[str] = None,
    ) -> List[str]:
        """Find source files and process them using aider.

        Depending on the `operates_on_whole_codebase` flag, this will either
        process files individually or all together.

        Args:
            directory: Directory to search for source files.
            specific_file: Optional specific file to process.
            message: Message to pass to aider. If None, uses the default message.

        Returns:
            List of files that were successfully processed.
        """
        # Use default message if none provided
        if message is None:
            message = self.get_default_message()

        # Determine the list of files to process
        if specific_file:
            source_files = [specific_file]
            # Force file-by-file if a specific file is given, regardless of flag?
            # For now, let the flag decide even for a single specific file.
        else:
            # Find source files in the directory using the imported function
            source_files = find_files(directory)

        if not source_files:
            print(f"No source files found in directory: {directory}", file=sys.stderr)
            return []

        processed_files: List[str] = []
        try:
            if self.operates_on_whole_codebase:
                # Process all files together
                if specific_file:
                    print(
                        f"Warning: --file option ignored because {self.__class__.__name__} operates on the whole codebase. Processing all found files.",
                        file=sys.stderr)
                if self._run_aider([], message):
                    processed_files = source_files  # Assume all were processed if aider succeeds
                # On failure, _run_aider prints error, processed_files remains empty
            else:
                # Process files one by one
                for file_path in source_files:
                    if self._run_aider([file_path], message):
                        processed_files.append(file_path)
                    # If _run_aider returns False, an error was already printed.
                    # Continue processing other files unless aider itself is not found.

        except FileNotFoundError:
            # Error already printed by _run_aider, just return empty list
            # The exception is caught here to prevent crashing the caller if aider isn't found
            return []

        return processed_files

    def run(self) -> int:
        """Run the code processor.

        Returns:
            Exit code (0 for success, non-zero for failure).
        """
        try:
            args = self.parse_args()

            # process_files now handles the --file vs operates_on_whole_codebase logic internally
            processed_files = self.process_files(
                args.directory, args.file, args.message
            )

            if processed_files is not None:  # Check if FileNotFoundError occurred in process_files
                print(f"\nProcessed {len(processed_files)} files:")
                for file in processed_files:
                    print(f"  - {file}")
            else:
                # Error message already printed if aider not found
                return 1  # Indicate failure

            return 0
        except FileNotFoundError:
            # This catches the re-raised FileNotFoundError from _run_aider
            # Error message already printed
            return 1
        except Exception as e:
            for file in processed_files:
                print(f"  - {file}")

            return 0
        except Exception as e:
            print(f"An unexpected error occurred: {e}", file=sys.stderr)
            return 1
