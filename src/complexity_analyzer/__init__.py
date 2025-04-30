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

        # Create a temporary file with the content of all reports
        temp_file_path = os.path.join(output_dir, "temp_complexity_reports.txt")
        with open(temp_file_path, "w") as temp_file:
            temp_file.write("Here are the individual complexity reports to combine:\n\n")
            for i, report_path in enumerate(report_files, 1):
                temp_file.write(f"Report {i}: {report_path}\n")
                try:
                    with open(report_path, "r") as report_file:
                        report_content = report_file.read()
                        temp_file.write(f"```json\n{report_content}\n```\n\n")
                except Exception as e:
                    temp_file.write(f"Error reading report: {e}\n\n")

        # Call aider to combine the reports
        try:
            import subprocess
            master_report_path = os.path.join(output_dir, "MASTER_COMPLEXITY_REPORT.json")

            # Create a temporary script to help aider generate the master report
            helper_script_path = os.path.join(output_dir, "combine_reports_helper.py")
            helper_script_content = '''
# Helper script to combine complexity reports
import json
import os
import sys

def combine_reports(reports_file, output_file):
    """Read reports from the text file and combine them into a master report."""
    # Parse the reports from the text file
    with open(reports_file, 'r') as f:
        content = f.read()

    # Extract JSON blocks
    import re
    json_blocks = re.findall(r'```json\\n(.+?)\\n```', content, re.DOTALL)

    all_components = []
    file_reports = []

    for json_block in json_blocks:
        try:
            report = json.loads(json_block)
            file_reports.append(report)

            # Add file path to each component for tracking
            for component in report.get("components", []):
                component["source_file"] = report.get("file_path", "unknown")
                all_components.append(component)
        except json.JSONDecodeError:
            print(f"Error parsing JSON block: {json_block[:100]}...")

    if not all_components:
        print("No valid components found in reports.")
        return False

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
        "average_changeability_score": sum(c.get("changeability_score", 0) for c in all_components) / len(all_components) if all_components else 0
    }

    # Create the master report
    master_report = {
        "summary": summary,
        "components": all_components
    }

    # Write the master report to a file
    with open(output_file, "w") as f:
        json.dump(master_report, f, indent=2)

    return True

if __name__ == "__main__":
    if len(sys.argv) != 3:
        print("Usage: python combine_reports_helper.py <reports_file> <output_file>")
        sys.exit(1)

    reports_file = sys.argv[1]
    output_file = sys.argv[2]

    if combine_reports(reports_file, output_file):
        print(f"Successfully created master report: {output_file}")
    else:
        print("Failed to create master report")
        sys.exit(1)
'''
            with open(helper_script_path, "w") as f:
                f.write(helper_script_content)

            # First, use aider to analyze the reports and generate insights
            command = ["aider", "--no-pretty", "--no-stream", "--yes-always", "--no-git", "--no-auto-commits",
                       "--message", combine_message, temp_file_path]
            print(f"Running aider to analyze complexity reports: {' '.join(command)}")
            subprocess.run(command, check=True, text=True)

            # Then use the helper script to actually combine the reports
            print("Generating master complexity report...")
            helper_command = ["python", helper_script_path, temp_file_path, master_report_path]
            subprocess.run(helper_command, check=True, text=True)

            # Clean up temporary files
            if os.path.exists(temp_file_path):
                os.remove(temp_file_path)
            if os.path.exists(helper_script_path):
                os.remove(helper_script_path)

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
