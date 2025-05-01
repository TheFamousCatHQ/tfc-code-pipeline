#!/usr/bin/env python3
"""
Processor to analyze code complexity using agno/LLM.
"""

import argparse
import glob
import logging
import os
import sys
from typing import List, Optional

# Import agno for direct LLM calls
from agno.agent import Agent
from agno.models.openrouter import OpenRouter

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
    """Processor for analyzing code complexity using agno/LLM."""

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
            help="Skip analysis for components where a COMPLEXITY_REPORT.json already exists"
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
            args = self.args # Use the stored args

            # If --show-only-repo-files-chunks is specified, let base class handle it
            if args.show_only_repo_files_chunks:
                return super().run() # Delegate to base class run for this flag

            # Normal processing mode: generate individual reports
            # The base class process_files will handle calling aider
            processed_files = self.process_files(args) # Pass the full args namespace

            if processed_files is None: # Indicates critical error like aider not found
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
                    return 1 # Indicate failure if combining fails
            else:
                logger.warning("No individual complexity reports found to combine.")
                # Decide if this is an error or just a state. If reports were expected, maybe return 1.
                # If it's possible no complex files were found, return 0.
                if not args.skip: # If we weren't skipping, not finding reports might be unexpected
                    logger.warning("No complex components identified in the analyzed files.")
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
        return "Analyze code complexity using an LLM via agno"

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
        """Combine multiple complexity reports into a master report using agno to call an LLM.

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
            "\nHere is the master schema for the MASTER_COMPLEXITY_REPORT.json file:\n"
            f"```json\n{schema_content}\n```\n"
        )

        # Use agno to call an LLM to combine the reports
        try:
            import json
            import shutil
            import requests

            # Determine the master report path
            if output_path:
                master_report_path = output_path
                # Ensure the directory exists
                os.makedirs(os.path.dirname(os.path.abspath(master_report_path)), exist_ok=True)
                logger.info(f"Using custom output path for master report: {master_report_path}")
            else:
                master_report_path = os.path.join(output_dir, "MASTER_COMPLEXITY_REPORT.json")
                logger.info(f"Using default output path for master report: {master_report_path}")

            # agno library is used directly

            # Load all report files into a single dictionary
            all_reports = []
            for report_file in report_files:
                try:
                    with open(report_file, 'r') as f:
                        report_data = json.load(f)
                        all_reports.append(report_data)
                    logger.debug(f"Loaded report from {report_file}")
                except Exception as e:
                    logger.warning(f"Error loading report {report_file}: {e}")

            # Create a temporary file with all reports
            temp_input_file = os.path.join(output_dir, "_temp_all_reports.json")
            with open(temp_input_file, 'w') as f:
                json.dump(all_reports, f)

            logger.info(f"Running agno to generate master complexity report with {len(report_files)} report files")

            # Set up agno to call the LLM
            model_name = "openrouter/gpt-4.1-nano"
            # Prepare the prompt for agno
            prompt = f"{combine_message}\n\nHere are all the reports to combine:\n"

            # Add the content of all reports to the prompt
            for i, report in enumerate(all_reports):
                prompt += f"\nReport {i+1}:\n```json\n{json.dumps(report, indent=2)}\n```\n"

            # Use agno library directly
            try:
                # Create an OpenRouter model instance
                model = OpenRouter(model=model_name)

                # Create an Agent instance with the model
                agent = Agent(model=model)

                # Run the agent with the prompt
                response = agent.run(prompt, stream=False, format="json")

                # Process the response from agno
                try:
                    # Check if response is already a dict (parsed JSON)
                    if isinstance(response, dict):
                        master_report = response
                    # Check if response is a string
                    elif isinstance(response, str):
                        # Try to find and parse JSON in the response string
                        json_start = response.find('{')
                        json_end = response.rfind('}')

                        if json_start >= 0 and json_end > json_start:
                            json_str = response[json_start:json_end+1]
                            master_report = json.loads(json_str)
                        else:
                            # If no JSON found, try to use the entire response
                            master_report = json.loads(response)
                    else:
                        # If response is neither dict nor string, try to convert to string and parse
                        response_str = str(response)
                        logger.warning(f"Unexpected response type: {type(response)}. Attempting to convert to string.")
                        master_report = json.loads(response_str)

                    # Write the master report to the output file
                    with open(master_report_path, 'w') as f:
                        json.dump(master_report, f, indent=2)

                    logger.info(f"Master report created at {master_report_path}")
                except Exception as e:
                    logger.error(f"Error processing agno response: {e}")
                    logger.debug(f"agno response: {response}")
                    return None

            except Exception as e:
                logger.error(f"Error running agno library: {e}")
                return None

            # Clean up temporary file
            if os.path.exists(temp_input_file):
                os.remove(temp_input_file)

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
                logger.info(f"Found {len(existing_reports)} existing complexity reports. Skipping analysis for these components.")
                # for report in existing_reports: # Debug logging if needed
                #     logger.debug(f"Existing report: {report}")

        # If a specific file is provided and skip is enabled, check if it already has a report
        if specific_file and skip:
            file_dir = os.path.dirname(os.path.abspath(specific_file))
            report_path = os.path.join(file_dir, "COMPLEXITY_REPORT.json")
            if os.path.exists(report_path):
                logger.info(f"Skipping analysis for {specific_file} as it already has a complexity report at {report_path}.")
                return [specific_file] # Return as processed (skipped)

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
                logger.info(f"Skipping analysis for {len(skipped_files_due_to_report)} files in directories with existing reports.")
                # logger.debug(f"Skipped files: {skipped_files_due_to_report}")

            if not files_to_process:
                logger.info("All found source files already have complexity reports or are in directories with reports. No new analysis needed.")
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
                    return None # Critical error from base class

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

    parser = argparse.ArgumentParser(description="Analyze code complexity using an LLM via agno")
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
