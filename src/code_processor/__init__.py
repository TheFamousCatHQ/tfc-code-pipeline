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
from collections import defaultdict
from pathlib import Path
from typing import Dict, List, Optional, Sequence

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
        parser.add_argument(
            "--show-only-repo-files-chunks",
            action="store_true",
            help="Only show the file chunks that would be processed, then exit without processing"
        )
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
        print(f"Found {len(file_chunks)} chunks with a total of {total_files} files")
        print(f"Chunking algorithm: min 10 files, max 20 files per chunk (when possible)")

        # Count chunks by size
        size_distribution = {}
        for chunk in file_chunks:
            chunk_size = len(chunk)
            if chunk_size not in size_distribution:
                size_distribution[chunk_size] = 0
            size_distribution[chunk_size] += 1

        # Display size distribution
        print("\nChunk size distribution:")
        for size in sorted(size_distribution.keys()):
            count = size_distribution[size]
            print(f"  - {size} files: {count} chunk{'s' if count > 1 else ''}")

        # Display detailed information about each chunk
        chunk_info = {}
        for chunk in file_chunks:
            if not chunk:  # Skip empty chunks (shouldn't happen)
                continue
            parent_dir = str(Path(chunk[0]).parent)
            if parent_dir not in chunk_info:
                chunk_info[parent_dir] = []
            chunk_info[parent_dir].append(len(chunk))

        print("\nDirectory breakdown:")
        for parent_dir, file_counts in chunk_info.items():
            chunk_count = len(file_counts)
            total_files_in_dir = sum(file_counts)
            if chunk_count == 1:
                print(f"  - Directory '{parent_dir}': 1 chunk with {total_files_in_dir} files")
            else:
                chunks_desc = ', '.join([str(count) for count in sorted(file_counts, reverse=True)])
                print(f"  - Directory '{parent_dir}': {chunk_count} chunks with {total_files_in_dir} files ({chunks_desc} files per chunk)")

        # Check for combined directories
        combined_dirs = set()
        for chunk in file_chunks:
            if not chunk:  # Skip empty chunks (shouldn't happen)
                continue
            dirs_in_chunk = set(str(Path(file_path).parent) for file_path in chunk)
            if len(dirs_in_chunk) > 1:
                combined_dirs.update(dirs_in_chunk)

        if combined_dirs:
            print("\nSmall directories combined into chunks:")
            for dir_name in sorted(combined_dirs):
                print(f"  - {dir_name}")

        # Display files in each chunk
        print("\nDetailed file listing by chunk:")
        for i, chunk in enumerate(file_chunks, 1):
            if not chunk:  # Skip empty chunks (shouldn't happen)
                continue

            # Get all unique parent directories in this chunk
            dirs_in_chunk = set(str(Path(file_path).parent) for file_path in chunk)
            if len(dirs_in_chunk) == 1:
                parent_dir = next(iter(dirs_in_chunk))
                print(f"\nChunk {i}/{len(file_chunks)}: {len(chunk)} files from directory: {parent_dir}")
            else:
                dir_list = ', '.join(sorted(dirs_in_chunk))
                print(f"\nChunk {i}/{len(file_chunks)}: {len(chunk)} files from multiple directories: {dir_list}")

            for j, file_path in enumerate(chunk, 1):
                print(f"  {j}. {file_path}")

    def _run_aider(self, files: List[str], message: str) -> bool:
        """Run aider with the specified files and message.

        Args:
            files: List of file paths to pass to aider.
            message: Message to pass to aider.

        Returns:
            True if aider ran successfully, False otherwise.
        """
        command = ["aider", "--no-pretty", "--no-stream", "--yes-always", "--no-git", "--no-auto-commits", "--message",
                   message] + files
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
                # Process files in chunks grouped by parent directory
                if specific_file:
                    print(
                        f"Warning: --file option ignored because {self.__class__.__name__} operates on the whole codebase. Processing all found files.",
                        file=sys.stderr)

                # Group files by parent directory with a maximum of 20 files per chunk
                file_chunks = self._group_files_by_parent_directory(source_files)

                # Display detailed information about the chunks
                print(f"Chunking algorithm: min 10 files, max 20 files per chunk (when possible)")
                total_files = sum(len(chunk) for chunk in file_chunks)
                print(f"Found {len(file_chunks)} chunks with a total of {total_files} files")

                # Count chunks by size
                size_distribution = {}
                for chunk in file_chunks:
                    chunk_size = len(chunk)
                    if chunk_size not in size_distribution:
                        size_distribution[chunk_size] = 0
                    size_distribution[chunk_size] += 1

                # Display size distribution
                print("\nChunk size distribution:")
                for size in sorted(size_distribution.keys()):
                    count = size_distribution[size]
                    print(f"  - {size} files: {count} chunk{'s' if count > 1 else ''}")

                # Display detailed information about each chunk
                chunk_info = {}
                for chunk in file_chunks:
                    if not chunk:  # Skip empty chunks (shouldn't happen)
                        continue
                    parent_dir = str(Path(chunk[0]).parent)
                    if parent_dir not in chunk_info:
                        chunk_info[parent_dir] = []
                    chunk_info[parent_dir].append(len(chunk))

                print("\nDirectory breakdown:")
                for parent_dir, file_counts in chunk_info.items():
                    chunk_count = len(file_counts)
                    total_files_in_dir = sum(file_counts)
                    if chunk_count == 1:
                        print(f"  - Directory '{parent_dir}': 1 chunk with {total_files_in_dir} files")
                    else:
                        chunks_desc = ', '.join([str(count) for count in sorted(file_counts, reverse=True)])
                        print(f"  - Directory '{parent_dir}': {chunk_count} chunks with {total_files_in_dir} files ({chunks_desc} files per chunk)")

                # Process each chunk separately
                for i, chunk in enumerate(file_chunks, 1):
                    if not chunk:  # Skip empty chunks (shouldn't happen)
                        continue

                    # Get all unique parent directories in this chunk
                    dirs_in_chunk = set(str(Path(file_path).parent) for file_path in chunk)
                    if len(dirs_in_chunk) == 1:
                        parent_dir = next(iter(dirs_in_chunk))
                        print(f"\nProcessing chunk {i}/{len(file_chunks)}: {len(chunk)} files from directory: {parent_dir}")
                    else:
                        dir_list = ', '.join(sorted(dirs_in_chunk))
                        print(f"\nProcessing chunk {i}/{len(file_chunks)}: {len(chunk)} files from multiple directories: {dir_list}")

                    if self._run_aider(chunk, message):
                        processed_files.extend(chunk)  # Add all files in the chunk to processed_files
                    # On failure, _run_aider prints error, we continue with the next chunk
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

            # If --show-only-repo-files-chunks is specified, just show the chunks and exit
            if args.show_only_repo_files_chunks:
                # Find source files
                if args.file:
                    source_files = [args.file]
                    print(f"Warning: Using specific file: {args.file}")
                else:
                    source_files = find_files(args.directory)

                if not source_files:
                    print(f"No source files found in directory: {args.directory}", file=sys.stderr)
                    return 1

                # Display the file chunks without processing
                self._display_file_chunks(source_files)
                return 0

            # Normal processing mode
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
            print(f"An unexpected error occurred: {e}", file=sys.stderr)
            return 1
