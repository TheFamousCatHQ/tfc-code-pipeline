#!/usr/bin/env python3
"""
Processor to analyze code complexity using aider/LLM.
"""

import glob
import json
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
        """Combine multiple complexity reports into a master report.

        Args:
            report_files: List of paths to complexity report files.
            output_dir: Directory where the master report will be saved.

        Returns:
            Path to the master report file, or None if no reports were found.
        """
        if not report_files:
            print("No complexity reports found to combine.")
            return None

        # Read all reports and combine them
        all_components = []
        file_reports = []

        for report_path in report_files:
            try:
                with open(report_path, "r") as f:
                    report_data = json.load(f)
                    file_reports.append(report_data)

                    # Add file path to each component for tracking
                    for component in report_data.get("components", []):
                        component["source_file"] = report_data.get("file_path", "unknown")
                        all_components.append(component)
            except Exception as e:
                print(f"Error reading report {report_path}: {e}")

        if not all_components:
            print("No valid components found in reports.")
            return None

        # Sort components by changeability_score (ascending)
        all_components.sort(key=lambda x: x.get("changeability_score", 100))

        # Create summary of most complex components (top 5 or all if less than 5)
        most_complex = all_components[:min(5, len(all_components))]
        summary = {
            "most_complex_components": [
                {
                    "name": component.get("name", "Unnamed"),
                    "file": component.get("source_file", "unknown"),
                    "changeability_score": component.get("changeability_score", 0),
                    "complexity_reason": component.get("complexity_reason", "")
                } for component in most_complex
            ],
            "total_components_analyzed": len(all_components),
            "total_files_analyzed": len(file_reports),
            "average_changeability_score": sum(c.get("changeability_score", 0) for c in all_components) / len(
                all_components) if all_components else 0
        }

        # Create the master report
        master_report = {
            "summary": summary,
            "components": all_components
        }

        # Write the master report to a file
        master_report_path = os.path.join(output_dir, "MASTER_COMPLEXITY_REPORT.json")
        try:
            with open(master_report_path, "w") as f:
                json.dump(master_report, f, indent=2)
            return master_report_path
        except Exception as e:
            print(f"Error writing master report: {e}")
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

        # For testing purposes: If no reports were found, create sample reports
        if not report_files and processed_files:
            raise Exception("No complexity reports found. Creating sample reports for testing...")

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
