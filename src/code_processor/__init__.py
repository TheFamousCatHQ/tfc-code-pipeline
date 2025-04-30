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

    def _process_single_file(self, file_path: str, message: str) -> bool:
        """Process a single file using aider.

        Args:
            file_path: Path to the file.
            message: Message to pass to aider.

        Returns:
            True if processing was successful, False otherwise.
        """
        print(f"Processing file: {file_path}")
        try:
            # Call aider with the single file and message
            subprocess.run(
                ["aider", "--message", message, file_path],
                check=True,
                text=True,
                # Consider adding capture_output=True if subclasses need output
            )
            return True
        except subprocess.CalledProcessError as e:
            print(f"Error processing file {file_path}: {e}", file=sys.stderr)
            return False
        except FileNotFoundError:
            print(
                "Error: 'aider' command not found. Please ensure it is installed.",
                file=sys.stderr,
            )
            # Re-raise or handle differently if needed for whole codebase mode?
            # For now, let it stop the whole process if aider isn't found.
            raise

    def _process_whole_codebase(
        self, file_paths: List[str], message: str
    ) -> List[str]:
        """Process multiple files together using aider.

        Args:
            file_paths: List of paths to the files.
            message: Message to pass to aider.

        Returns:
            List of files processed (assuming aider processes all or fails).
        """
        print(f"Processing {len(file_paths)} files together...")
        try:
            # Call aider with the message and all files
            command = ["aider", "--message", message]
            print(f"Running command: {' '.join(command)}") # For debugging
            subprocess.run(
                command,
                check=True,
                text=True,
            )
            # If successful, assume all input files were processed in the session
            return file_paths
        except subprocess.CalledProcessError as e:
            print(f"Error processing codebase: {e}", file=sys.stderr)
            return [] # Return empty list on failure
        except FileNotFoundError:
            print(
                "Error: 'aider' command not found. Please ensure it is installed.",
                file=sys.stderr,
            )
            raise

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
            # Find source files in the directory
            # Ensure find_source_files is imported correctly
            try:
                from find_source_files import find_source_files as find_files
            except ImportError:
                 # Handle potential import issues if running from different contexts
                 # This might need adjustment based on project structure/testing
                from src.find_source_files import find_source_files as find_files
            source_files = find_files(directory)

        if not source_files:
            print(f"No source files found in directory: {directory}", file=sys.stderr)
            return []

        processed_files: List[str] = []
        try:
            if self.operates_on_whole_codebase:
                # Process all files together
                if specific_file:
                    print(f"Warning: --file option ignored because {self.__class__.__name__} operates on the whole codebase.", file=sys.stderr)
                processed_files = self._process_whole_codebase(source_files, message)
            else:
                # Process files one by one
                for file_path in source_files:
                    if self._process_single_file(file_path, message):
                        processed_files.append(file_path)
                    # If _process_single_file returns False, an error was already printed.
                    # Should we stop processing remaining files on first error?
                    # Current behavior: continue processing other files.

        except FileNotFoundError:
             # Error already printed by helper methods, just return empty list
             return []

        return processed_files

    def run(self) -> int:
        """Run the code processor.

        Returns:
            Exit code (0 for success, non-zero for failure).
        """
        try:
            args = self.parse_args()

            # Handle --file specifically if processor operates on whole codebase
            effective_specific_file = args.file
            if self.operates_on_whole_codebase and args.file:
                 print(f"Warning: --file option ignored because {self.__class__.__name__} operates on the whole codebase. Analyzing full directory.", file=sys.stderr)
                 effective_specific_file = None # Effectively ignore --file

            processed_files = self.process_files(
                args.directory, effective_specific_file, args.message
            )

            print(f"\nProcessed {len(processed_files)} files:")
            for file in processed_files:
                print(f"  - {file}")

            return 0
        except Exception as e:
            print(f"Error: {e}", file=sys.stderr)
            return 1
