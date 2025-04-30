#!/usr/bin/env python3
"""
Script to write unit tests for source files using aider.

This script finds source files in a specified directory using find-source-files
and then calls aider for each file with a message to write unit tests without using mocks.
"""

import sys

try:
    from code_processor import CodeProcessor
except ImportError:
    # When running tests, the import path is different
    from src.code_processor import CodeProcessor


class WriteTestsProcessor(CodeProcessor):
    """Processor for writing unit tests using aider."""

    operates_on_whole_codebase: bool = False
    """Writing tests operates on a file-by-file basis."""

    def get_default_message(self) -> str:
        """Get the default message to pass to aider.

        Returns:
            Default message for aider.
        """
        return "write unit tests without using mocks for all functions found in this file. If tests already exist, check if they are up to date, if not update them to cover the current functionality."

    def get_description(self) -> str:
        """Get the description for the argument parser.

        Returns:
            Description string.
        """
        return "Write unit tests for source files using aider"


def main() -> int:
    """Run the main script.

    Returns:
        Exit code (0 for success, non-zero for failure).
    """
    processor = WriteTestsProcessor()
    return processor.run()


if __name__ == "__main__":
    sys.exit(main())
