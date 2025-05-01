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
from typing import Dict, List, Optional, Sequence

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

        return parser.parse_args(args)

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
        for parent_dir, file_counts in chunk_info.items():
            chunk_count = len(file_counts)
            total_files_in_dir = sum(file_counts)
            if chunk_count == 1:
                logger.info(f"  - Directory '{parent_dir}': 1 chunk with {total_files_in_dir} files")
            else:
                chunks_desc = ', '.join([str(count) for count in sorted(file_counts, reverse=True)])
                logger.info(f"  - Directory '{parent_dir}': {chunk_count} chunks with {total_files_in_dir} files ({chunks_desc} files per chunk)")

        # Check for combined directories
        combined_dirs = set()
        for chunk in file_chunks:
            if not chunk:  # Skip empty chunks (shouldn't happen)
                continue
            dirs_in_chunk = set(str(Path(file_path).parent) for file_path in chunk)
            if len(dirs_in_chunk) > 1:
                combined_dirs.update(dirs_in_chunk)

        if combined_dirs:
            logger.info("Small directories combined into chunks:")
            for dir_name in sorted(combined_dirs):
                logger.info(f"  - {dir_name}")

        # Display files in each chunk
        logger.info("Detailed file listing by chunk:")
        for i, chunk in enumerate(file_chunks, 1):
            if not chunk:  # Skip empty chunks (shouldn't happen)
                continue

            # Get all unique parent directories in this chunk
            dirs_in_chunk = set(str(Path(file_path).parent) for file_path in chunk)
            if len(dirs_in_chunk) == 1:
                parent_dir = next(iter(dirs_in_chunk))
                logger.info(f"Chunk {i}/{len(file_chunks)}: {len(chunk)} files from directory: {parent_dir}")
            else:
                dir_list = ', '.join(sorted(dirs_in_chunk))
                logger.info(f"Chunk {i}/{len(file_chunks)}: {len(chunk)} files from multiple directories: {dir_list}")

            for j, file_path in enumerate(chunk, 1):
                logger.debug(f"  {j}. {file_path}")

    def _run_aider(self, files: List[str], message: str, debug: bool = False) -> bool:
        """Run aider with the specified files and message.

        Args:
            files: List of file paths to pass to aider.
            message: Message to pass to aider.
            debug: Whether to run aider with debug flags (--pretty and --stream).

        Returns:
            True if aider ran successfully, False otherwise.
        """
        if debug:
            command = ["aider", "--pretty", "--stream", "--yes-always", "--no-git", "--no-auto-commits", "--message",
                      message] + files
        else:
            command = ["aider", "--no-pretty", "--no-stream", "--yes-always", "--no-git", "--no-auto-commits", "--message",
                      message] + files
        logger.debug(f"Running command: {' '.join(command)}")

        start_time = time.time()
        try:
            # Capture the output from aider
            result = subprocess.run(
                command,
                check=True,
                text=True,
                capture_output=True
            )

            # Calculate execution time
            execution_time = time.time() - start_time
            logger.info(f"Aider execution completed in {execution_time:.2f} seconds")

            # Log aider output
            if result.stdout:
                logger.debug("--- Aider Output Start ---")
                logger.debug(f"{result.stdout}")
                logger.debug("--- Aider Output End ---")

            # Log any error output
            if result.stderr:
                logger.warning("--- Aider Warnings/Errors ---")
                logger.warning(f"{result.stderr}")
                logger.warning("--- End of Warnings/Errors ---")

            return True
        except subprocess.CalledProcessError as e:
            # Calculate execution time even for failures
            execution_time = time.time() - start_time
            logger.error(f"Aider execution failed after {execution_time:.2f} seconds")

            file_list = ', '.join(files)
            logger.error(f"Error processing file(s) {file_list}: {e}")

            # Log any captured output from the failed run
            if e.stdout:
                logger.debug("--- Aider Output Before Failure ---")
                logger.debug(f"{e.stdout}")
                logger.debug("--- End of Output ---")

            if e.stderr:
                logger.error("--- Aider Error Output ---")
                logger.error(f"{e.stderr}")
                logger.error("--- End of Error Output ---")

            return False
        except FileNotFoundError:
            # This error is critical, stop the process.
            logger.critical("Error: 'aider' command not found. Please ensure it is installed and in your PATH.")
            raise  # Re-raise to stop execution in run()

    def process_files(
            self,
            directory: str,
            specific_file: Optional[str] = None,
            message: Optional[str] = None,
            debug: bool = False,
    ) -> List[str]:
        """Find source files and process them using aider.

        Depending on the `operates_on_whole_codebase` flag, this will either
        process files individually or all together.

        Args:
            directory: Directory to search for source files.
            specific_file: Optional specific file to process.
            message: Message to pass to aider. If None, uses the default message.
            debug: Whether to run aider with debug flags (--pretty and --stream).

        Returns:
            List of files that were successfully processed.
        """
        # Start timing the entire process
        process_start_time = time.time()

        # Use default message if none provided
        if message is None:
            message = self.get_default_message()

        # Determine the list of files to process
        logger.info("Step 1: Finding source files...")
        file_discovery_start = time.time()

        if specific_file:
            source_files = [specific_file]
            # Force file-by-file if a specific file is given, regardless of flag?
            # For now, let the flag decide even for a single specific file.
        else:
            # Find source files in the directory using the imported function
            source_files = find_files(directory)

        file_discovery_time = time.time() - file_discovery_start
        logger.info(f"File discovery completed in {file_discovery_time:.2f} seconds")

        if not source_files:
            logger.error(f"No source files found in directory: {directory}")
            return []

        processed_files: List[str] = []
        try:
            if self.operates_on_whole_codebase:
                # Process files in chunks grouped by parent directory
                if specific_file:
                    logger.warning(
                        f"Warning: --file option ignored because {self.__class__.__name__} operates on the whole codebase. Processing all found files.")

                # Group files by parent directory with a maximum of 20 files per chunk
                logger.info("Step 2: Grouping files by parent directory...")
                chunking_start = time.time()
                file_chunks = self._group_files_by_parent_directory(source_files)
                chunking_time = time.time() - chunking_start
                logger.info(f"File chunking completed in {chunking_time:.2f} seconds")

                # Display detailed information about the chunks
                logger.info(f"Chunking algorithm: min 10 files, max 20 files per chunk (when possible)")
                total_files = sum(len(chunk) for chunk in file_chunks)
                logger.info(f"Found {len(file_chunks)} chunks with a total of {total_files} files")

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
                for parent_dir, file_counts in chunk_info.items():
                    chunk_count = len(file_counts)
                    total_files_in_dir = sum(file_counts)
                    if chunk_count == 1:
                        logger.info(f"  - Directory '{parent_dir}': 1 chunk with {total_files_in_dir} files")
                    else:
                        chunks_desc = ', '.join([str(count) for count in sorted(file_counts, reverse=True)])
                        logger.info(f"  - Directory '{parent_dir}': {chunk_count} chunks with {total_files_in_dir} files ({chunks_desc} files per chunk)")

                # Process each chunk separately
                logger.info("Step 3: Processing files with aider...")
                for i, chunk in enumerate(file_chunks, 1):
                    if not chunk:  # Skip empty chunks (shouldn't happen)
                        continue

                    # Get all unique parent directories in this chunk
                    dirs_in_chunk = set(str(Path(file_path).parent) for file_path in chunk)
                    if len(dirs_in_chunk) == 1:
                        parent_dir = next(iter(dirs_in_chunk))
                        logger.info(f"Processing chunk {i}/{len(file_chunks)}: {len(chunk)} files from directory: {parent_dir}")
                    else:
                        dir_list = ', '.join(sorted(dirs_in_chunk))
                        logger.info(f"Processing chunk {i}/{len(file_chunks)}: {len(chunk)} files from multiple directories: {dir_list}")

                    if self._run_aider(chunk, message, debug):
                        processed_files.extend(chunk)  # Add all files in the chunk to processed_files
                    # On failure, _run_aider logs error, we continue with the next chunk
            else:
                # Process files one by one
                logger.info("Step 2: Processing files with aider one by one...")
                for file_path in source_files:
                    logger.info(f"Processing file: {file_path}")
                    if self._run_aider([file_path], message, debug):
                        processed_files.append(file_path)
                    # If _run_aider returns False, an error was already logged.
                    # Continue processing other files unless aider itself is not found.

        except FileNotFoundError:
            # Error already logged by _run_aider, just return empty list
            # The exception is caught here to prevent crashing the caller if aider isn't found
            return []

        # Calculate and display total processing time
        total_processing_time = time.time() - process_start_time
        logger.info(f"Total processing time: {total_processing_time:.2f} seconds")

        return processed_files

    def run(self) -> int:
        """Run the code processor.

        Returns:
            Exit code (0 for success, non-zero for failure).
        """
        try:
            args = self.parse_args()

            # Configure logging if debug flag is set
            if hasattr(args, 'debug') and args.debug:
                configure_logging(verbose=True)

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
            processed_files = self.process_files(
                args.directory, args.file, args.message, args.debug
            )

            if processed_files is not None:  # Check if FileNotFoundError occurred in process_files
                logger.info(f"Processed {len(processed_files)} files:")
                for file in processed_files:
                    logger.info(f"  - {file}")
            else:
                # Error message already logged if aider not found
                return 1  # Indicate failure

            return 0
        except FileNotFoundError:
            # This catches the re-raised FileNotFoundError from _run_aider
            # Error message already logged
            return 1
        except Exception as e:
            logger.error(f"An unexpected error occurred: {e}")
            return 1


def configure_logging(verbose: bool = False):
    """Configure logging for the code processor.

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
