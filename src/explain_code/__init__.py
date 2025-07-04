#!/usr/bin/env python3
"""
Script to explain code in source files using aider.

This script finds source files in a specified directory using find-source-files
and then calls aider for each file with the message "explain this code".
"""

import sys

from code_processor import CodeProcessor


class ExplainCodeProcessor(CodeProcessor):
    """Processor for explaining code using aider."""

    operates_on_whole_codebase: bool = False
    """Explain code operates on a file-by-file basis."""

    def get_default_message(self) -> str:
        """Get the default message to pass to aider.

        Returns:
            Default message for aider.
        """
        return "explain this code"

    def get_description(self) -> str:
        """Get the description for the argument parser.

        Returns:
            Description string.
        """
        return "Explain code in source files using aider"


def main() -> int:
    """Run the main script.

    Returns:
        Exit code (0 for success, non-zero for failure).
    """
    processor = ExplainCodeProcessor()
    return processor.run()


if __name__ == "__main__":
    sys.exit(main())
