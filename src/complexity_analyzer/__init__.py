#!/usr/bin/env python3
"""
Processor to analyze code complexity using pydantic-ai/LLM.
"""

import argparse
import glob
import json
import logging
import os
import sys
from typing import List, Optional, Dict, Any

from logging_utils import get_logger

from pydantic import BaseModel, Field

try:
    # Try importing directly
    from ai import create_agent
except ImportError:
    # Fall back to src-prefixed import
    from src.ai import create_agent

# Set up logging
logger = get_logger()


# Pydantic models for the master complexity report
class ComplexComponent(BaseModel):
    """Model for a complex component in a file."""
    name: str = Field(description="Name of the component (function, class, method, etc.)")
    line_range: List[int] = Field(description="Start and end line numbers of the component", min_items=2, max_items=2)
    complexity_reason: str = Field(description="Explanation of why the component is considered complex")
    changeability_score: int = Field(
        description="Score indicating how easy it is to make changes to this component (0-100, where 0 is impossible and 100 is super easy)",
        ge=0, le=100)
    improvement_suggestions: str = Field(
        description="Suggestions for simplifying or improving the readability of this component")
    llm_improvement_prompt: str = Field(
        description="A specific prompt for an LLM to improve or resolve this complexity issue")


class FileReport(BaseModel):
    """Model for a complexity report for a single file."""
    file_path: str = Field(description="Path to the analyzed source code file")
    components: List[ComplexComponent] = Field(description="List of complex components identified in the file")


class MostComplexComponent(BaseModel):
    """Model for a summary of a complex component."""
    name: str = Field(description="Name of the component")
    file_path: str = Field(description="Path to the file containing the component")
    changeability_score: int = Field(description="Changeability score of the component", ge=0, le=100)


class Summary(BaseModel):
    """Model for the summary section of the master report."""
    total_files_analyzed: int = Field(description="Total number of files analyzed", ge=0)
    total_components_analyzed: int = Field(description="Total number of components analyzed across all files", ge=0)
    average_changeability_score: float = Field(description="Average changeability score across all components", ge=0,
                                               le=100)
    most_complex_components: List[MostComplexComponent] = Field(
        description="List of the most complex components across the entire codebase")


class MasterComplexityReport(BaseModel):
    """Model for the master complexity report."""
    summary: Summary = Field(description="Summary statistics and highlights of the most complex components")
    detailed_reports: List[FileReport] = Field(description="List of complexity reports for individual files")


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
    """Processor for analyzing code complexity using pydantic-ai/LLM."""

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
        parser.add_argument(
            "--skip",
            action="store_true",
            help="Skip generating individual reports and only generate the master report from existing COMPLEXITY_REPORTs"
        )

    def run(self) -> int:
        """Run the code processor.

        Overrides the base class method to handle complexity-specific logic
        like combining reports.

        Returns:
            Exit code (0 for success, non-zero for failure).
        """
        try:
            # Ensure args are parsed (usually done by base class run)
            if self.args is None:
                self.parse_args()
            args = self.args  # Use the stored args

            # If --show-only-repo-files-chunks is specified, let base class handle it
            if args.show_only_repo_files_chunks:
                return super().run()  # Delegate to base class run for this flag

            # Check if we should skip individual report generation
            if hasattr(args, 'skip') and args.skip:
                logger.info("Skipping individual report generation as --skip flag is used.")
                processed_files = []  # No files processed as we're skipping
            else:
                # Normal processing mode: generate individual reports
                # The base class process_files will handle calling aider
                processed_files = self.process_files(args)  # Pass the full args namespace

                if processed_files is None:  # Indicates critical error like aider not found
                    logger.error("Complexity analysis failed due to a critical error during file processing.")
                    return 1

                logger.info(f"\nInitial complexity analysis generated reports for {len(processed_files)} files.")

            # Combine reports (logic moved from process_files to run)
            logger.info("Combining complexity reports into a master report...")
            report_files = self._find_complexity_reports(args.directory)

            if report_files:
                logger.info(f"Found {len(report_files)} complexity reports to combine.")
                # Determine output path for the master report
                output_path = args.output if hasattr(args, 'output') and args.output else None
                master_report_path = self._combine_complexity_reports(report_files, args.directory, output_path)
                if master_report_path and os.path.exists(master_report_path):
                    logger.info(f"Master complexity report created successfully: {master_report_path}")
                else:
                    logger.error("Failed to create or validate the master complexity report.")
                    return 1  # Indicate failure if combining fails
            else:
                logger.warning("No individual complexity reports found to combine.")
                # Decide if this is an error or just a state. If reports were expected, maybe return 1.
                # If it's possible no complex files were found, return 0.
                if not args.skip:  # If we weren't skipping, not finding reports might be unexpected
                    logger.warning("No complex components identified in the analyzed files.")
                else:
                    logger.warning("No existing COMPLEXITY_REPORT.json files found in the directory.")
                # Assuming success if processing ran but no reports generated

            return 0
        except FileNotFoundError:
            # Error message already logged by base class or _run_aider
            return 1
        except Exception as e:
            logger.exception(f"An unexpected error occurred in ComplexityAnalyzerProcessor run: {e}")
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
        return "Analyze code complexity using an LLM via pydantic-ai"

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

    def _combine_complexity_reports(self, report_files: List[str], output_dir: str,
                                    output_path: Optional[str] = None) -> Optional[str]:
        """Combine multiple complexity reports into a master report using pydantic-ai to call an LLM.

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

        # Determine the master report path
        if output_path:
            master_report_path = output_path
            # Ensure the directory exists
            os.makedirs(os.path.dirname(os.path.abspath(master_report_path)), exist_ok=True)
            logger.info(f"Using custom output path for master report: {master_report_path}")
        else:
            master_report_path = os.path.join(output_dir, "MASTER_COMPLEXITY_REPORT.json")
            logger.info(f"Using default output path for master report: {master_report_path}")

        try:
            # Load all report files
            all_reports = []
            for report_file in report_files:
                try:
                    with open(report_file, 'r') as f:
                        report_data = json.load(f)
                        all_reports.append(report_data)
                    logger.debug(f"Loaded report from {report_file}")
                except Exception as e:
                    logger.warning(f"Error loading report {report_file}: {e}")

            if not all_reports:
                logger.error("No valid reports could be loaded.")
                return None

            logger.info(f"Using pydantic-ai to generate master complexity report with {len(report_files)} report files")

            # Create a system prompt for the agent
            system_prompt = """
            Generate a master complexity report by combining multiple individual reports.

            Instructions:
            - Combine all components from all reports into a single comprehensive report
            - Add a summary section with statistics and the most complex components
            - Sort components by changeability_score (ascending) so the most difficult components are listed first
            - Include total_files_analyzed, total_components_analyzed, and average_changeability_score
            - Preserve all fields from the original reports, including the 'llm_improvement_prompt' field
            """

            # Create an agent using the ai module
            agent = create_agent(
                output_type=MasterComplexityReport,
                system_prompt=system_prompt
            )

            # Generate the master report
            try:
                master_report = agent.run(all_reports)
                logger.info("Successfully generated master report using pydantic-ai")

                # Convert to dict and write to file
                master_report_dict = master_report.model_dump()
                with open(master_report_path, 'w') as f:
                    json.dump(master_report_dict, f, indent=2)

                logger.info(f"Master report created at {master_report_path}")

            except Exception as e:
                logger.error(f"Error generating master report with pydantic-ai: {e}")
                logger.debug("Exception details:", exc_info=True)
                return None

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

    def process_files(self, args: argparse.Namespace) -> Optional[List[str]]:
        """Find source files and process them using aider to generate complexity reports.

        Overrides the base class method to handle skipping and then calls the base method.

        Args:
            args: Parsed command-line arguments namespace.

        Returns:
            List of files that were processed (or skipped), or None on critical failure.
        """
        directory = args.directory
        specific_file = args.file
        skip = args.skip if hasattr(args, 'skip') else False

        # --- Skip Logic --- Find existing reports if skip is enabled
        existing_reports = []
        if skip:
            existing_reports = self._find_complexity_reports(directory)
            if existing_reports:
                logger.info(
                    f"Found {len(existing_reports)} existing complexity reports. Skipping analysis for these components.")
                # for report in existing_reports: # Debug logging if needed
                #     logger.debug(f"Existing report: {report}")

        # If a specific file is provided and skip is enabled, check if it already has a report
        if specific_file and skip:
            file_dir = os.path.dirname(os.path.abspath(specific_file))
            report_path = os.path.join(file_dir, "COMPLEXITY_REPORT.json")
            if os.path.exists(report_path):
                logger.info(
                    f"Skipping analysis for {specific_file} as it already has a complexity report at {report_path}.")
                return [specific_file]  # Return as processed (skipped)

        files_to_process = []
        skipped_files_due_to_report = []

        # Determine which files actually need processing by aider
        if skip and not specific_file:
            source_files = find_files(directory)
            if not source_files:
                logger.warning(f"No source files found in directory {directory}. Nothing to process or skip.")
                return []

            for file_path in source_files:
                file_dir = os.path.dirname(os.path.abspath(file_path))
                report_path = os.path.join(file_dir, "COMPLEXITY_REPORT.json")
                if os.path.exists(report_path):
                    skipped_files_due_to_report.append(file_path)
                else:
                    files_to_process.append(file_path)

            if skipped_files_due_to_report:
                logger.info(
                    f"Skipping analysis for {len(skipped_files_due_to_report)} files in directories with existing reports.")
                # logger.debug(f"Skipped files: {skipped_files_due_to_report}")

            if not files_to_process:
                logger.info(
                    "All found source files already have complexity reports or are in directories with reports. No new analysis needed.")
                # Return all original source files as they were all accounted for (processed or skipped)
                return source_files

            # Create a temporary args object for the base class call, overriding the file list
            # This seems overly complex. The base class should handle filtering internally if needed?
            # Let's reconsider: The base `process_files` should perhaps take the list of files to process?

            # --- Simpler Approach: Let the base class process everything found, then filter later? --- No, skip should prevent aider calls.
            # --- Alternative: Modify base class `process_files` to accept an explicit list? --- Maybe too complex.
            # --- Current approach: Call base class ONLY with the files needing processing --- This seems reasonable.

            # Create a modified args object for the super call if we are processing a subset
            if skipped_files_due_to_report:
                # We need to trick the base class into processing only `files_to_process`
                # The base class uses args.file or args.directory. If args.file is set, it uses that.
                # If we set args.file to a specific file, it won't work for multiple files.
                # We can't easily override the file finding in the base class without more changes.

                # --- Best approach: Let the base class find all files, but only run aider on the ones needed --- #
                # This requires modifying the base `_run_aider` or the loop in `process_files`.
                # Let's stick to calling the base class for the whole directory for now,
                # and the base class logic will handle chunking. The skip logic here primarily determines
                # if *any* processing is needed. The master report generation happens later anyway.

                logger.info(f"Proceeding to analyze {len(files_to_process)} files that do not have existing reports.")
                # Let the base class handle processing all files found in the directory
                # The `operates_on_whole_codebase` flag ensures aider runs once with all files.
                processed_by_aider = super().process_files(args)

                # The result includes files processed by aider. We need to return the union
                # of files processed by aider and files skipped due to existing reports.
                if processed_by_aider is None:
                    return None  # Critical error from base class

                # Combine skipped files and files actually processed by aider
                final_processed_list = list(set(processed_by_aider + skipped_files_due_to_report))
                return final_processed_list
            else:
                # No skipping needed, just process everything found by the base class
                return super().process_files(args)

        else:
            # No skip, or specific file without skip, or specific file that needs processing
            # Let the base class handle finding and processing files normally
            return super().process_files(args)


def configure_logging(verbose: bool = False):
    """Configure logging for the complexity analyzer.

    Args:
        verbose: Whether to enable verbose (DEBUG) logging.
    """
    try:
        # Try importing directly (for Docker/installed package)
        from logging_utils import configure_logging as setup_logging
    except ImportError:
        # Fall back to src-prefixed import (for local development)
        from src.logging_utils import configure_logging as setup_logging

    # Configure logging using the centralized function
    setup_logging(verbose, module_name="complexity_analyzer")


def main() -> int:
    """Run the main script.

    Returns:
        Exit code (0 for success, non-zero for failure).
    """
    import argparse

    parser = argparse.ArgumentParser(description="Analyze code complexity using an LLM via pydantic-ai")
    parser.add_argument("--verbose", "-v", action="store_true", help="Enable verbose logging")
    parser.add_argument("--schema-validation", action="store_true",
                        help="Enable detailed schema validation logging")

    # Parse only the known args to avoid conflicts with the parent parser
    args, _ = parser.parse_known_args()

    # Configure logging
    configure_logging(args.verbose)

    # Set validation module logging level if schema-validation is enabled
    if args.schema_validation:
        validation_logger = get_logger('validate_complexity_report')
        validation_logger.setLevel(logging.DEBUG)
        logger.info("Detailed schema validation logging enabled")

    processor = ComplexityAnalyzerProcessor()
    return processor.run()


if __name__ == "__main__":
    sys.exit(main())
