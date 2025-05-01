#!/usr/bin/env python3
"""
Base module for processing code files using aider.

This module provides a base class for scripts that process code files using aider,
such as explaining code or writing tests.
"""

import argparse
import logging
import subprocess
import sys
import time
from abc import ABC, abstractmethod
from collections import defaultdict
from pathlib import Path
from typing import Dict, List, Optional, Sequence, Union

# Set up logging
logger = logging.getLogger(__name__)

try:
    # Try importing directly (for Docker/installed package)
    from find_source_files import find_source_files as find_files
except ImportError:
    # Fall back to src-prefixed import (for local development)
    from src.find_source_files import find_source_files as find_files


class CodeProcessor(ABC):
    """Base class for processing code files using aider."""

    # --- Configuration Properties (Subclasses can override) ---

    operates_on_whole_codebase: bool = False
    """Whether this processor operates on the whole codebase at once (True)
       or on a file-by-file basis (False)."""

    args: argparse.Namespace
    """Parsed command-line arguments."""

    def __init__(self, args: Optional[Union[argparse.Namespace, Sequence[str]]] = None):
        """Initialize the CodeProcessor.

        Args:
            args: Pre-parsed arguments (Namespace) or sequence of strings to parse.
                  If None, parsing is deferred until self.parse_args or self.run is called.
                  If an empty list, parsing is also deferred.
        """
        if isinstance(args, argparse.Namespace):
            # Args already parsed
            self.args = args
        elif isinstance(args, Sequence) and args: # Check if it's a non-empty sequence
            # Parse the provided sequence of strings immediately
            self.args = self.parse_args(list(args))
        else:
            # Defer parsing (args is None or an empty sequence)
            self.args = None # type: ignore

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

    def add_arguments(self, parser: argparse.ArgumentParser) -> None:
        """Add processor-specific command-line arguments to the parser.

        Subclasses can override this method to add their own command-line arguments.

        Args:
            parser: The argument parser to add arguments to.
        """
        pass

    def parse_args(self, args: Optional[Sequence[str]] = None) -> argparse.Namespace:
        """Parse command-line arguments and store them in self.args.

        Args:
            args: Command line arguments. Defaults to None, which uses sys.argv[1:].

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
        parser.add_argument(
            "--show-only-repo-files-chunks",
            action="store_true",
            help="Only show the file chunks that would be processed, then exit without processing"
        )
        parser.add_argument(
            "--debug",
            action="store_true",
            help="Run aider with --pretty and --stream flags for debugging"
        )

        # Allow subclasses to add their own arguments
        self.add_arguments(parser)

        # Store parsed args
        parsed_args = parser.parse_args(args)
        self.args = parsed_args
        return parsed_args

    # --- Core Processing Logic ---

    def _group_files_by_parent_directory(self, files: List[str], min_files_per_chunk: int = 10, max_files_per_chunk: int = 20) -> List[List[str]]:
        """Group files by parent directory and ensure each chunk has between min_files_per_chunk and max_files_per_chunk files.

        Args:
            files: List of file paths to group.
            min_files_per_chunk: Minimum number of files per chunk (when possible).
            max_files_per_chunk: Maximum number of files per chunk.

        Returns:
            List of lists, where each inner list contains files from the same parent directory,
            with between min_files_per_chunk and max_files_per_chunk files per list (when possible).
        """
        # Group files by parent directory
        dir_to_files: Dict[str, List[str]] = defaultdict(list)
        for file_path in files:
            parent_dir = str(Path(file_path).parent)
            dir_to_files[parent_dir].append(file_path)

        # Create chunks with min-max constraints
        chunks: List[List[str]] = []

        # Process directories with enough files for at least one full chunk first
        large_dirs = {d: f for d, f in dir_to_files.items() if len(f) >= min_files_per_chunk}
        small_dirs = {d: f for d, f in dir_to_files.items() if len(f) < min_files_per_chunk}

        # Process large directories
        for parent_dir, dir_files in large_dirs.items():
            # If a directory has more than max_files_per_chunk files, split it optimally
            if len(dir_files) <= max_files_per_chunk:
                # If files fit in a single chunk, keep them together
                chunks.append(dir_files)
            else:
                # Calculate optimal chunk size to minimize the number of small chunks
                total_files = len(dir_files)
                num_full_chunks = total_files // max_files_per_chunk
                remainder = total_files % max_files_per_chunk

                # If the remainder is less than min_files_per_chunk, distribute the files more evenly
                if 0 < remainder < min_files_per_chunk:
                    # Calculate a new chunk size that's between min and max
                    new_chunk_size = total_files // (num_full_chunks + 1)
                    if new_chunk_size < min_files_per_chunk:
                        # If we can't meet the minimum, use max size for all but the last chunk
                        for i in range(0, total_files - remainder, max_files_per_chunk):
                            chunk = dir_files[i:i + max_files_per_chunk]
                            chunks.append(chunk)
                        # Add the remainder as the last chunk
                        if remainder > 0:
                            chunks.append(dir_files[-remainder:])
                    else:
                        # Create evenly sized chunks
                        for i in range(0, total_files, new_chunk_size):
                            end_idx = min(i + new_chunk_size, total_files)
                            chunk = dir_files[i:end_idx]
                            chunks.append(chunk)
                else:
                    # Create full-sized chunks
                    for i in range(0, total_files - remainder, max_files_per_chunk):
                        chunk = dir_files[i:i + max_files_per_chunk]
                        chunks.append(chunk)
                    # Add the remainder as the last chunk if it's large enough
                    if remainder >= min_files_per_chunk or remainder == 0:
                        if remainder > 0:
                            chunks.append(dir_files[-remainder:])
                    else:
                        # Redistribute the last chunk + remainder to meet the minimum size
                        last_full_chunk = chunks.pop() if chunks else []
                        combined = last_full_chunk + dir_files[-remainder:]
                        # Split the combined chunk more evenly
                        mid = len(combined) // 2
                        chunks.append(combined[:mid])
                        chunks.append(combined[mid:])

        # Process small directories by combining them when possible
        if small_dirs:
            combined_small_files = []
            for dir_files in small_dirs.values():
                combined_small_files.extend(dir_files)

            # If we have enough small files to meet the minimum, create chunks
            if combined_small_files:
                if len(combined_small_files) >= min_files_per_chunk:
                    # Create chunks of size between min and max
                    for i in range(0, len(combined_small_files), max_files_per_chunk):
                        end_idx = min(i + max_files_per_chunk, len(combined_small_files))
                        chunk = combined_small_files[i:end_idx]
                        # Only add chunks that meet the minimum size
                        if len(chunk) >= min_files_per_chunk or i + max_files_per_chunk >= len(combined_small_files):
                            chunks.append(chunk)
                else:
                    # If we don't have enough small files to meet the minimum,
                    # add them as a single chunk anyway
                    chunks.append(combined_small_files)

        return chunks

    def _display_file_chunks(self, source_files: List[str]) -> None:
        """Display information about the file chunks without processing them.

        Args:
            source_files: List of source files to group into chunks.
        """
        # Group files by parent directory
        file_chunks = self._group_files_by_parent_directory(source_files)

        # Display summary information
        total_files = sum(len(chunk) for chunk in file_chunks)
        logger.info(f"Found {len(file_chunks)} chunks with a total of {total_files} files")
        logger.info(f"Chunking algorithm: min 10 files, max 20 files per chunk (when possible)")

        # Count chunks by size
        size_distribution = {}
        for chunk in file_chunks:
            chunk_size = len(chunk)
            if chunk_size not in size_distribution:
                size_distribution[chunk_size] = 0
            size_distribution[chunk_size] += 1

        # Display size distribution
        logger.info("Chunk size distribution:")
        for size in sorted(size_distribution.keys()):
            count = size_distribution[size]
            logger.info(f"  - {size} files: {count} chunk{'s' if count > 1 else ''}")

        # Display detailed information about each chunk
        chunk_info = {}
        for chunk in file_chunks:
            if not chunk:  # Skip empty chunks (shouldn't happen)
                continue
            parent_dir = str(Path(chunk[0]).parent)
            if parent_dir not in chunk_info:
                chunk_info[parent_dir] = []
            chunk_info[parent_dir].append(len(chunk))

        logger.info("Directory breakdown:")
        for parent_dir, chunk_sizes in sorted(chunk_info.items()):
            logger.info(f"  - {parent_dir}: {len(chunk_sizes)} chunk{'s' if len(chunk_sizes) > 1 else ''} ({sum(chunk_sizes)} files)")
            # Optionally print individual chunk sizes per directory
            # logger.info(f"    Sizes: {sorted(chunk_sizes)}")

    def _run_aider(self, files: List[str], message: str, debug: bool = False) -> bool:
        """Run aider command with the given files and message.

        Args:
            files: List of files to pass to aider.
            message: Message to pass to aider.
            debug: Whether to run aider with debug flags (--pretty and --stream).

        Returns:
            True if aider ran successfully, False otherwise.
        """
        aider_cmd = [
            "aider",
            "--yes",
            "--model=openrouter/gpt-4.1-nano"
        ]
        if debug:
            aider_cmd.extend(["--pretty", "--stream"])

        # Filter out any empty strings or None values from files
        valid_files = [f for f in files if f]
        if not valid_files:
            logger.warning("No valid files provided to aider. Skipping aider run.")
            return True # No files, technically not a failure of aider itself

        aider_cmd.extend(valid_files)
        aider_cmd.extend(["--message", message])

        logger.info(f"Running aider with {len(valid_files)} files...")
        logger.debug(f"Aider command: {' '.join(aider_cmd)}")
        try:
            # Run aider command
            process = subprocess.Popen(aider_cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)

            # Log aider output in real-time
            if process.stdout:
                for line in iter(process.stdout.readline, ''):
                    logger.info(f"[aider] {line.strip()}")
            if process.stderr:
                for line in iter(process.stderr.readline, ''):
                    logger.error(f"[aider stderr] {line.strip()}")

            process.wait()

            if process.returncode == 0:
                logger.info(f"Aider processing completed successfully for {len(valid_files)} files.")
                return True
            else:
                logger.error(f"Aider failed with exit code {process.returncode}")
                return False
        except FileNotFoundError:
            logger.error("Error: 'aider' command not found. Make sure aider is installed and in your PATH.")
            logger.error("You can install aider using: pip install aider-chat")
            # Re-raise the exception to be caught by the main run loop
            raise
        except Exception as e:
            logger.error(f"An error occurred while running aider: {e}")
            return False

    def process_files(self, args: argparse.Namespace) -> Optional[List[str]]:
        """Find source files and process them using aider.

        Args:
            args: Parsed command-line arguments containing directory, file, message, etc.

        Returns:
            List of files that were successfully processed, or None if a critical error occurred (e.g., aider not found).
        """
        # Find source files
        if args.file:
            source_files = [args.file]
            logger.info(f"Processing specific file: {args.file}")
        else:
            source_files = find_files(args.directory)
            if not source_files:
                logger.warning(f"No source files found in directory: {args.directory}")
                return []
            logger.info(f"Found {len(source_files)} source files in {args.directory}")

        # Determine the message to use
        message = args.message if args.message else self.get_default_message()

        processed_files_list = []
        start_time = time.time()

        try:
            if self.operates_on_whole_codebase:
                logger.info("Processor operates on whole codebase. Running aider once.")
                if self._run_aider(source_files, message, args.debug):
                    processed_files_list = source_files
                else:
                    logger.error("Aider failed while processing the whole codebase.")
                    # Returning None might be too drastic if only one chunk failed
                    # Consider returning the list of files attempted
                    return source_files # Indicate which files were attempted
            else:
                logger.info("Processor operates file-by-file (chunked).")
                # Group files by parent directory
                file_chunks = self._group_files_by_parent_directory(source_files)
                total_chunks = len(file_chunks)
                logger.info(f"Processing {len(source_files)} files in {total_chunks} chunks...")

                for i, chunk in enumerate(file_chunks):
                    chunk_start_time = time.time()
                    logger.info(f"--- Processing Chunk {i + 1}/{total_chunks} ({len(chunk)} files) ---")
                    if self._run_aider(chunk, message, args.debug):
                        processed_files_list.extend(chunk)
                        chunk_duration = time.time() - chunk_start_time
                        logger.info(f"--- Chunk {i + 1}/{total_chunks} completed successfully in {chunk_duration:.2f}s ---")
                    else:
                        logger.error(f"--- Chunk {i + 1}/{total_chunks} failed ---: {chunk}")
                        # Continue processing other chunks even if one fails
                        continue

        except FileNotFoundError:
            # Aider not found, handled by _run_aider logging, re-raise to stop execution
            logger.critical("Aider not found. Cannot continue processing.")
            return None # Indicate critical failure
        except Exception as e:
            logger.error(f"An unexpected error occurred during file processing: {e}", exc_info=True)
            # Depending on severity, you might return processed_files_list or None
            return processed_files_list # Return files processed so far

        end_time = time.time()
        total_duration = end_time - start_time
        logger.info(f"Finished processing {len(processed_files_list)} files in {total_duration:.2f} seconds.")

        return processed_files_list

    def run(self) -> int:
        """Run the code processor.

        Returns:
            Exit code (0 for success, non-zero for failure).
        """
        try:
            # Parse args if not already parsed during __init__
            if self.args is None:
                self.parse_args()

            # Now self.args is guaranteed to be set
            args = self.args

            # Configure logging based on args (assuming a --verbose or similar arg might be added)
            configure_logging(getattr(args, 'verbose', False))

            # If --show-only-repo-files-chunks is specified, just show the chunks and exit
            if args.show_only_repo_files_chunks:
                # Find source files
                if args.file:
                    source_files = [args.file]
                    logger.warning(f"Using specific file: {args.file}")
                else:
                    source_files = find_files(args.directory)

                if not source_files:
                    logger.error(f"No source files found in directory: {args.directory}")
                    return 1

                # Display the file chunks without processing
                self._display_file_chunks(source_files)
                return 0

            # Normal processing mode
            processed_files = self.process_files(args) # Pass the full args namespace

            if processed_files is not None:  # Check if None was returned due to critical error
                logger.info(f"\nSuccessfully processed {len(processed_files)} files.")
                # Optionally list processed files if needed, but logger already did
                # for file in processed_files:
                #     logger.debug(f"  - {file}")
            else:
                logger.error("Processing failed due to a critical error (e.g., aider not found).")
                return 1  # Indicate failure

            return 0
        except FileNotFoundError:
            # This catches the FileNotFoundError if re-raised from _run_aider/process_files
            # Error message already logged
            return 1
        except Exception as e:
            logger.exception(f"An unexpected error occurred in the main run loop: {e}")
            return 1


def configure_logging(verbose: bool = False):
    """Configure logging for the code processor.

    Args:
        verbose: Whether to enable verbose (DEBUG) logging.
    """
    # Set up root logger
    root_logger = logging.getLogger()

    # Remove existing handlers if configuring multiple times
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

# Example usage (for illustration, typically run via subclass main)
# if __name__ == "__main__":
#     # This part would need a concrete implementation of CodeProcessor
#     # For example:
#     # class MyProcessor(CodeProcessor):
#     #     def get_default_message(self) -> str: return "/ask Explain this code."
#     #     def get_description(self) -> str: return "Explains code using aider."
#
#     # processor = MyProcessor()
#     # sys.exit(processor.run())
#     print("This script provides a base class. Run a specific processor script instead.")
#     sys.exit(1)
