#!/usr/bin/env python3
"""
Script to find potential bugs in source files using aider.

This script analyzes source files in a specified directory using find-source-files
and then calls aider to identify potential bugs, generating a JSON output with
bug details including location, line number, filename, explanation, confidence, and severity.
"""

import json
import os
import re
import subprocess
import sys
from typing import Dict, List, Optional, Any

from logging_utils import get_logger

# Set up logging
logger = get_logger()

# Import relative to the 'src' package
from code_processor import CodeProcessor
# Import relative to the 'src' package
from find_source_files import find_source_files as find_files


class FindBugsProcessor(CodeProcessor):
    """Processor for finding potential bugs in code using aider."""

    def get_default_message(self) -> str:
        """Get the default message to pass to aider.

        Returns:
            Default message for aider.
        """
        return (
            "Analyze this code and identify potential bugs. I am not interested in general suggestions for improvements just hard, plain bugs like off-by-one-errors."
            "For each issue found, provide: 1) a brief description, 2) the line number(s), 3) severity (high/medium/low), 4) confidence level (high/medium/low), and 5) a suggested fix."
            "Your output will be an artifact name FILENAME-bugreport.json")

    def get_description(self) -> str:
        """Get the description for the argument parser.

        Returns:
            Description string.
        """
        return "Find potential bugs in source files and output results as JSON"

    def process_files(self, directory: str, specific_file: Optional[str] = None, message: Optional[str] = None) -> List[
        str]:
        """Find source files and process them using aider to identify bugs.

        Args:
            directory: Directory to search for source files.
            specific_file: Optional specific file to process.
            message: Message to pass to aider. If None, uses the default message.

        Returns:
            List of files that were processed.
        """
        # Use default message if none provided
        if message is None:
            message = self.get_default_message()

        # If a specific file is provided, only process that file
        if specific_file:
            source_files = [specific_file]
        else:
            # Find source files in the directory (find_files is imported at module level now)
            source_files = find_files(directory)

        if not source_files:
            logger.warning(f"No source files found in directory: {directory}", file=sys.stderr)
            return []

        # Process each file with aider and collect bug information
        processed_files = []
        bugs_list = []

        for file_path in source_files:
            logger.info(f"Processing file: {file_path}")
            try:
                # Create a temporary file to capture aider output
                temp_output_file = f"{file_path}.aider_output.txt"

                # Call aider with the file and message, capturing output
                result = subprocess.run(
                    ["aider", "--message", message, file_path],
                    check=True,
                    text=True,
                    capture_output=True
                )

                # Save output to temporary file
                with open(temp_output_file, "w") as f:
                    f.write(result.stdout)

                # Parse the output to extract bug information
                bugs = self._parse_aider_output(result.stdout, file_path)
                if bugs:
                    bugs_list.extend(bugs)

                # Clean up temporary file
                if os.path.exists(temp_output_file):
                    os.remove(temp_output_file)

                processed_files.append(file_path)
            except subprocess.CalledProcessError as e:
                logger.error(f"Error processing file {file_path}: {e}")
            except FileNotFoundError:
                logger.error("Error: 'aider' command not found. Please ensure it is installed.")
                break

        # Write the bugs list to a JSON file
        output_file = os.path.join(directory, "bugs_report.json")
        with open(output_file, "w") as f:
            json.dump(bugs_list, f, indent=2)

        logger.info(f"Bug report saved to: {output_file}")
        logger.info(f"Found {len(bugs_list)} potential issues across {len(processed_files)} files.")

        return processed_files

    def _parse_aider_output(self, output: str, file_path: str) -> List[Dict[str, Any]]:
        """Parse aider output to extract bug information.

        Args:
            output: The output from aider.
            file_path: The path to the file that was processed.

        Returns:
            A list of dictionaries containing bug information.
        """
        bugs = []

        # Extract bug information using regex patterns
        # Look for patterns like "Line 42: Description" or "Lines 42-45: Description"
        line_patterns = [
            r"Line[s]?\s+(\d+)(?:-(\d+))?\s*:\s*(.+?)(?=Line|\Z)",  # Line X: Description
            r"On line[s]?\s+(\d+)(?:-(\d+))?\s*:\s*(.+?)(?=On line|\Z)",  # On line X: Description
        ]

        # Look for severity and confidence indicators
        severity_pattern = r"severity\s*[:-]\s*(high|medium|low)"
        confidence_pattern = r"confidence\s*[:-]\s*(high|medium|low)"

        # Process the output
        current_bug = None

        # Try to extract structured bug information
        for pattern in line_patterns:
            matches = re.finditer(pattern, output, re.IGNORECASE | re.DOTALL)
            for match in matches:
                start_line = int(match.group(1))
                end_line = int(match.group(2)) if match.group(2) else start_line
                description = match.group(3).strip()

                # Look for severity and confidence in the description
                severity_match = re.search(severity_pattern, description, re.IGNORECASE)
                severity = severity_match.group(1).lower() if severity_match else "medium"

                confidence_match = re.search(confidence_pattern, description, re.IGNORECASE)
                confidence = confidence_match.group(1).lower() if confidence_match else "medium"

                bugs.append({
                    "filename": file_path,
                    "start_line": start_line,
                    "end_line": end_line,
                    "description": description,
                    "severity": severity,
                    "confidence": confidence
                })

        # If no structured bugs were found, try to extract general issues
        if not bugs:
            # Look for any mentions of issues, bugs, or problems
            issue_patterns = [
                r"issue[s]?:?\s*(.+?)(?=issue|\Z)",
                r"bug[s]?:?\s*(.+?)(?=bug|\Z)",
                r"problem[s]?:?\s*(.+?)(?=problem|\Z)",
                r"vulnerability:?\s*(.+?)(?=vulnerability|\Z)"
            ]

            for pattern in issue_patterns:
                matches = re.finditer(pattern, output, re.IGNORECASE | re.DOTALL)
                for match in matches:
                    description = match.group(1).strip()
                    if description:
                        bugs.append({
                            "filename": file_path,
                            "start_line": 0,  # Unknown line number
                            "end_line": 0,
                            "description": description,
                            "severity": "medium",
                            "confidence": "low"
                        })

        # If still no bugs found but aider provided some output, create a general entry
        if not bugs and output.strip():
            bugs.append({
                "filename": file_path,
                "start_line": 0,
                "end_line": 0,
                "description": "Potential issues may exist but could not be automatically extracted. Please review the full aider output.",
                "severity": "low",
                "confidence": "low"
            })

        return bugs


def configure_logging(verbose: bool = False):
    """Configure logging for the find_bugs module.

    Args:
        verbose: Whether to enable verbose (DEBUG) logging.
    """
    from logging_utils import configure_logging as setup_logging

    # Configure logging using the centralized function
    setup_logging(verbose, module_name="find_bugs")


def main() -> int:
    """Run the main script.

    Returns:
        Exit code (0 for success, non-zero for failure).
    """
    # Configure logging
    configure_logging()

    processor = FindBugsProcessor()
    return processor.run()


if __name__ == "__main__":
    sys.exit(main())
