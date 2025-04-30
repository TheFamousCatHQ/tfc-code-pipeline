#!/usr/bin/env python3
"""
Processor to analyze code complexity using aider/LLM.
"""

import sys

from code_processor import CodeProcessor


class ComplexityAnalyzerProcessor(CodeProcessor):
    """Processor for analyzing code complexity using aider/LLM."""

    operates_on_whole_codebase: bool = True
    """This processor analyzes the context of the whole codebase."""

    def get_default_message(self) -> str:
        """Get the default message to pass to aider.

        Returns:
            Default message for aider.
        """
        return (
            "Analyze this code to identify the most complex and difficult-to-understand parts.\n"
            "For each complex component you identify, please explain:\n"
            "1. Why it is considered complex (e.g., high cognitive load, complex logic, deep nesting, unclear naming, potential for bugs).\n"
            "2. Rate the ability to make changes to this component from 0 (impossible) to 100 (super eays).\n"
            "3. Suggestions for simplifying or improving the readability of this section.\n"
            "Focus on areas that would be challenging for a LLM to make changes to.\n"
            "Only analyze source code, no documentation, etc.\n"
            "Create a COMPLEXITY_REPORT.json with your findings.\n"
            "Add all files you need yourself to the context without asking or waiting for user actions.\n"
        )

    def get_description(self) -> str:
        """Get the description for the argument parser.

        Returns:
            Description string.
        """
        return "Analyze code complexity using an LLM via aider"

    # No need to override process_files, use the base class implementation
    # which calls aider with the message.


def main() -> int:
    """Run the main script.

    Returns:
        Exit code (0 for success, non-zero for failure).
    """
    processor = ComplexityAnalyzerProcessor()
    return processor.run()


if __name__ == "__main__":
    sys.exit(main())
