#!/usr/bin/env python3
"""
Processor to analyze code complexity using aider/LLM.
"""

import glob
import os
import sys
from typing import List, Optional

try:
    # Try importing directly (for Docker/installed package)
    from code_processor import CodeProcessor
except ImportError:
    # Fall back to src-prefixed import (for local development)
    from src.code_processor import CodeProcessor


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
            "2. Rate the ability to make changes to this component from 0 (impossible) to 100 (super easy).\n"
            "3. Suggestions for simplifying or improving the readability of this section.\n"
            "Focus on areas that would be challenging for a LLM to make changes to.\n"
            "Only analyze source code, no documentation, etc.\n"
            "Create a COMPLEXITY_REPORT.json with your findings in the following format:\n"
            "```json\n"
            "{\n"
            "  \"file_path\": \"path/to/file.py\",\n"
            "  \"components\": [\n"
            "    {\n"
            "      \"name\": \"component name\",\n"
            "      \"line_range\": [start_line, end_line],\n"
            "      \"complexity_reason\": \"explanation of why it's complex\",\n"
            "      \"changeability_score\": 0-100,\n"
            "      \"improvement_suggestions\": \"suggestions for improvement\"\n"
            "    }\n"
            "  ]\n"
            "}\n"
            "```\n"
            "Add all files you need yourself to the context without asking or waiting for user actions.\n"
        )

    def get_description(self) -> str:
        """Get the description for the argument parser.

        Returns:
            Description string.
        """
        return "Analyze code complexity using an LLM via aider"

    def _find_complexity_reports(self, directory: str) -> List[str]:
        """Find all COMPLEXITY_REPORT.json files in the directory.

        Args:
            directory: Directory to search for complexity reports.

        Returns:
            List of paths to complexity report files.
        """
        # Use glob to find all COMPLEXITY_REPORT.json files in the directory and subdirectories
        report_pattern = os.path.join(directory, "**", "COMPLEXITY_REPORT.json")
        return glob.glob(report_pattern, recursive=True)

    def _combine_complexity_reports(self, report_files: List[str], output_dir: str) -> Optional[str]:
        """Combine multiple complexity reports into a master report using aider.

        Args:
            report_files: List of paths to complexity report files.
            output_dir: Directory where the master report will be saved.

        Returns:
            Path to the master report file, or None if no reports were found.
        """
        if not report_files:
            print("No complexity reports found to combine.")
            return None

        # Create a message for aider to combine the reports
        combine_message = (
            "I have multiple COMPLEXITY_REPORT.json files that need to be combined into a master report.\n"
            "Each report contains complexity analysis for different parts of the codebase.\n"
            "Please combine all these reports into a single comprehensive MASTER_COMPLEXITY_REPORT.json file.\n"
            "The master report should maintain the same structure but combine all components from all files.\n"
            "Also add a summary section that highlights the most complex components across the entire codebase.\n"
            "Sort the components by changeability_score (ascending) so the most difficult components are listed first.\n"
            "Include statistics like total components analyzed, total files analyzed, and average changeability score.\n"
        )

        # Call aider directly with all report files as arguments
        try:
            import subprocess
            master_report_path = os.path.join(output_dir, "MASTER_COMPLEXITY_REPORT.json")

            # Build the command with all report files as arguments
            command = [
                          "aider", "--no-pretty", "--no-stream", "--yes-always", "--no-git", "--no-auto-commits",
                          "--message", combine_message
                      ] + report_files

            print(f"Running aider to generate master complexity report with {len(report_files)} report files")
            print(f"Command: {' '.join(command)}")

            # Run aider with all report files
            subprocess.run(command, check=True, text=True)

            # Check if the master report was created
            if os.path.exists(master_report_path):
                return master_report_path
            else:
                print("Master report file was not created.")
                return None
        except Exception as e:
            print(f"Error combining complexity reports: {e}")
            return None

    def process_files(
            self,
            directory: str,
            specific_file: Optional[str] = None,
            message: Optional[str] = None,
    ) -> List[str]:
        """Find source files and process them using aider, then combine the reports.

        Args:
            directory: Directory to search for source files.
            specific_file: Optional specific file to process.
            message: Message to pass to aider. If None, uses the default message.

        Returns:
            List of files that were successfully processed.
        """
        # First round: Process files to generate individual complexity reports
        processed_files = super().process_files(directory, specific_file, message)

        if not processed_files:
            return []

        print("\nFirst round of complexity analysis complete.")
        print("Starting second round: Combining complexity reports into a master report...")

        # Second round: Find and combine all complexity reports
        report_files = self._find_complexity_reports(directory)

        # Check if any complexity reports were found
        if not report_files and processed_files:
            print("No complexity reports found after processing files.")

        if report_files:
            print(f"Found {len(report_files)} complexity reports to combine.")
            master_report_path = self._combine_complexity_reports(report_files, directory)
            if master_report_path and os.path.exists(master_report_path):
                print(f"\nMaster complexity report created: {master_report_path}")
            else:
                print("Failed to create master complexity report.")
        else:
            print("No complexity reports found to combine.")

        return processed_files


def main() -> int:
    """Run the main script.

    Returns:
        Exit code (0 for success, non-zero for failure).
    """
    processor = ComplexityAnalyzerProcessor()
    return processor.run()


if __name__ == "__main__":
    sys.exit(main())
