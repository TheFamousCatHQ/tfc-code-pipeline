#!/usr/bin/env python3
"""
Processor to analyze code complexity using aider/LLM.
"""

import argparse
import glob
import json
import logging
import os
import sys
from typing import Dict, List, Optional, Any, Tuple

# Set up logging
logger = logging.getLogger(__name__)

try:
    # Try importing directly
    from validate_complexity_report import validate_and_fix_complexity_report
except ImportError:
    # Fall back to src-prefixed import
    from src.validate_complexity_report import validate_and_fix_complexity_report

try:
    # Try importing directly (for Docker/installed package)
    from code_processor import CodeProcessor
    from find_source_files import find_source_files as find_files
except ImportError:
    # Fall back to src-prefixed import (for local development)
    from src.code_processor import CodeProcessor
    from src.find_source_files import find_source_files as find_files


class ComplexityAnalyzerProcessor(CodeProcessor):
    """Processor for analyzing code complexity using aider/LLM."""

    operates_on_whole_codebase: bool = True
    """This processor analyzes the context of the whole codebase."""

    def add_arguments(self, parser: argparse.ArgumentParser) -> None:
        """Add processor-specific command-line arguments to the parser.

        Args:
            parser: The argument parser to add arguments to.
        """
        parser.add_argument(
            "-o", "--output",
            type=str,
            help="Path where the master complexity report will be saved"
        )

    def run(self) -> int:
        """Run the code processor.

        Overrides the base class method to pass the output path to process_files.

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
                args.directory, args.file, args.message, args.output if hasattr(args, 'output') else None
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
            "4. Create a specific prompt for an LLM that would help it improve or resolve this exact complexity issue.\n"
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
            "      \"improvement_suggestions\": \"suggestions for improvement\",\n"
            "      \"llm_improvement_prompt\": \"specific prompt for an LLM to improve or resolve this complexity issue\"\n"
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

    def _combine_complexity_reports(self, report_files: List[str], output_dir: str, output_path: Optional[str] = None) -> Optional[str]:
        """Combine multiple complexity reports into a master report using aider.

        Args:
            report_files: List of paths to complexity report files.
            output_dir: Directory where the master report will be saved if output_path is not specified.
            output_path: Optional specific path where the master report will be saved.

        Returns:
            Path to the master report file, or None if no reports were found.
        """
        if not report_files:
            logger.info("No complexity reports found to combine.")
            return None

        # Find the schema file
        schema_path = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))),
                                  "master_complexity_report_schema.json")

        # Check if schema exists, if not, look in doc directory
        if not os.path.exists(schema_path):
            schema_path = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))),
                                     "doc", "master_complexity_report_schema.json")

        # Read the schema file if it exists
        schema_content = ""
        if os.path.exists(schema_path):
            try:
                with open(schema_path, 'r') as schema_file:
                    schema_content = schema_file.read()
                logger.info(f"Successfully read schema from {schema_path}")
            except Exception as e:
                logger.warning(f"Failed to read schema file: {e}")
                schema_content = "Schema file could not be read."
        else:
            logger.warning("Schema file not found.")
            schema_content = "Schema file not found."

        # Create a message for aider to combine the reports
        combine_message = (
            "I have multiple COMPLEXITY_REPORT.json files that need to be combined into a master report.\n"
            "Each report contains complexity analysis for different parts of the codebase.\n"
            "Please combine all these reports into a single comprehensive MASTER_COMPLEXITY_REPORT.json file.\n"
            "The master report should maintain the same structure but combine all components from all files.\n"
            "Also add a summary section that highlights the most complex components across the entire codebase.\n"
            "Sort the components by changeability_score (ascending) so the most difficult components are listed first.\n"
            "Include statistics like total components analyzed, total files analyzed, and average changeability score.\n"
            "Make sure to preserve all fields from the original reports, including the 'llm_improvement_prompt' field.\n"
            "\nHere is the schema for the MASTER_COMPLEXITY_REPORT.json file:\n"
            f"{schema_content}\n"
        )

        # Call aider directly with all report files as arguments
        try:
            import subprocess

            # Determine the master report path
            if output_path:
                master_report_path = output_path
                # Ensure the directory exists
                os.makedirs(os.path.dirname(os.path.abspath(master_report_path)), exist_ok=True)
                logger.info(f"Using custom output path for master report: {master_report_path}")
            else:
                master_report_path = os.path.join(output_dir, "MASTER_COMPLEXITY_REPORT.json")
                logger.info(f"Using default output path for master report: {master_report_path}")

            # Build the command with all report files as arguments
            command = [
                          "aider", "--no-pretty", "--no-stream", "--yes-always", "--no-git", "--no-auto-commits",
                          "--message", combine_message
                      ] + report_files

            logger.info(f"Running aider to generate master complexity report with {len(report_files)} report files")
            logger.debug(f"Command: {' '.join(command)}")

            # Run aider with all report files
            subprocess.run(command, check=True, text=True)

            # Check if the master report was created
            if os.path.exists(master_report_path):
                # Validate the master report against the schema
                schema_path = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))),
                                          "master_complexity_report_schema.json")

                # Check if schema exists, if not, look in doc directory
                if not os.path.exists(schema_path):
                    schema_path = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))),
                                             "doc", "master_complexity_report_schema.json")

                if os.path.exists(schema_path):
                    logger.info(f"Schema validation: Found schema at {schema_path}")
                    logger.info(f"Schema validation: Validating master report against schema")

                    # Check if OPENROUTER_API_KEY is set
                    if not os.environ.get("OPENROUTER_API_KEY"):
                        logger.warning("Schema validation: OPENROUTER_API_KEY environment variable not set. "
                                      "If validation fails, automatic fixing will not be possible.")

                    success, result = validate_and_fix_complexity_report(master_report_path, schema_path)

                    if success:
                        logger.info(f"Schema validation: Master report validation successful")
                        logger.info(f"Schema validation: Final report saved at {result}")
                        return master_report_path
                    else:
                        logger.error(f"Schema validation: Error validating master report: {result}")
                        return None
                else:
                    logger.warning("Schema validation: Schema file not found. Skipping validation.")
                    logger.debug(f"Schema validation: Looked for schema at {schema_path}")
                    return master_report_path
            else:
                logger.error("Master report file was not created.")
                return None
        except Exception as e:
            logger.error(f"Error combining complexity reports: {e}")
            logger.debug(f"Exception details: {str(e)}", exc_info=True)
            return None

    def process_files(
            self,
            directory: str,
            specific_file: Optional[str] = None,
            message: Optional[str] = None,
            output_path: Optional[str] = None,
    ) -> List[str]:
        """Find source files and process them using aider, then combine the reports.

        Args:
            directory: Directory to search for source files.
            specific_file: Optional specific file to process.
            message: Message to pass to aider. If None, uses the default message.
            output_path: Optional path where the master report will be saved.

        Returns:
            List of files that were successfully processed.
        """
        # First round: Process files to generate individual complexity reports
        processed_files = super().process_files(directory, specific_file, message)

        if not processed_files:
            return []

        logger.info("First round of complexity analysis complete.")
        logger.info("Starting second round: Combining complexity reports into a master report...")

        # Second round: Find and combine all complexity reports
        report_files = self._find_complexity_reports(directory)

        # Check if any complexity reports were found
        if not report_files and processed_files:
            logger.warning("No complexity reports found after processing files.")

        if report_files:
            logger.info(f"Found {len(report_files)} complexity reports to combine.")
            master_report_path = self._combine_complexity_reports(report_files, directory, output_path)
            if master_report_path and os.path.exists(master_report_path):
                logger.info(f"Master complexity report created: {master_report_path}")
            else:
                logger.error("Failed to create master complexity report.")
        else:
            logger.warning("No complexity reports found to combine.")

        return processed_files


def configure_logging(verbose: bool = False):
    """Configure logging for the complexity analyzer.

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


def main() -> int:
    """Run the main script.

    Returns:
        Exit code (0 for success, non-zero for failure).
    """
    import argparse

    parser = argparse.ArgumentParser(description="Analyze code complexity using an LLM via aider")
    parser.add_argument("--verbose", "-v", action="store_true", help="Enable verbose logging")
    parser.add_argument("--schema-validation", action="store_true",
                        help="Enable detailed schema validation logging")

    # Parse only the known args to avoid conflicts with the parent parser
    args, _ = parser.parse_known_args()

    # Configure logging
    configure_logging(args.verbose)

    # Set validation module logging level if schema-validation is enabled
    if args.schema_validation:
        validation_logger = logging.getLogger('validate_complexity_report')
        validation_logger.setLevel(logging.DEBUG)
        logger.info("Detailed schema validation logging enabled")

    processor = ComplexityAnalyzerProcessor()
    return processor.run()


if __name__ == "__main__":
    sys.exit(main())
