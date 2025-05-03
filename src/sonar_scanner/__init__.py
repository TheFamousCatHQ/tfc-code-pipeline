#!/usr/bin/env python3
"""
Processor to run sonar-scanner on the whole codebase.
"""

import argparse
import json
import logging
import os
import subprocess
import sys
from typing import List, Optional

try:
    # Try importing directly (for Docker/installed package)
    from sonar_scanner.client import SonarQubeClient
except ImportError:
    # Fall back to src-prefixed import (for local development)
    from src.sonar_scanner.client import SonarQubeClient

try:
    # Try importing directly (for Docker/installed package)
    from code_processor import CodeProcessor
except ImportError:
    # Fall back to src-prefixed import (for local development)
    from src.code_processor import CodeProcessor

try:
    # Try importing directly (for Docker/installed package)
    from find_source_files import find_source_files as find_files
except ImportError:
    # Fall back to src-prefixed import (for local development)
    from src.find_source_files import find_source_files as find_files

# Set up logging
logger = logging.getLogger(__name__)


class SonarScannerProcessor(CodeProcessor):
    """Processor for running sonar-scanner on the whole codebase."""

    operates_on_whole_codebase: bool = True
    """This processor operates on the whole codebase."""

    def get_default_message(self) -> str:
        pass

    def _create_sonar_properties_file(self, directory: str, args: argparse.Namespace) -> None:
        """Create a sonar-project.properties file in the source directory.

        Args:
            directory: Directory where the file will be created.
            args: Parsed command-line arguments namespace.
        """
        # Get the name of the original source directory from environment variables
        # If not available, fall back to the name of the current directory
        source_dir_name = os.environ.get("ORIGINAL_SRC_DIR_NAME", os.path.basename(os.path.abspath(directory)))

        # Get the SONAR_TOKEN from command-line arguments or environment variables
        sonar_token = args.login if hasattr(args, 'login') and args.login else os.environ.get("SONAR_TOKEN", "")

        # Create the content for the sonar-project.properties file
        content = f"""sonar.projectKey={source_dir_name}
sonar.projectVersion=1.0
sonar.sources=.
sonar.host.url=https://sonar.thefamouscat.com
sonar.token={sonar_token}
"""

        # Create the file in the source directory
        properties_file_path = os.path.join(directory, "sonar-project.properties")
        logger.info(f"Creating sonar-project.properties file at {properties_file_path}")

        try:
            with open(properties_file_path, "w") as f:
                f.write(content)
            logger.info("sonar-project.properties file created successfully")
        except Exception as e:
            logger.error(f"Error creating sonar-project.properties file: {e}")
            # Continue with the process even if file creation fails

    def add_arguments(self, parser: argparse.ArgumentParser) -> None:
        """Add processor-specific command-line arguments to the parser.

        Args:
            parser: The argument parser to add arguments to.
        """
        parser.add_argument(
            "-p", "--project-key",
            type=str,
            help="SonarQube project key"
        )
        parser.add_argument(
            "--host-url",
            type=str,
            help="SonarQube host URL"
        )
        parser.add_argument(
            "--login",
            type=str,
            help="SonarQube authentication token"
        )
        parser.add_argument(
            "--sources",
            type=str,
            help="Comma-separated list of source directories to scan (relative to project root)"
        )
        parser.add_argument(
            "--exclusions",
            type=str,
            help="Comma-separated list of file path patterns to exclude from analysis"
        )
        parser.add_argument(
            "--skip-scanner",
            action="store_true",
            help="Skip sonar-scanner invocation and just output the measures"
        )

    def get_description(self) -> str:
        """Get the description for the argument parser.

        Returns:
            Description string.
        """
        return "Run sonar-scanner on the codebase or just output measures"

    def run(self) -> int:
        """Run the sonar-scanner processor.

        Returns:
            Exit code (0 for success, non-zero for failure).
        """
        try:
            # Parse args if not already parsed during __init__
            if self.args is None:
                self.parse_args()

            # Now self.args is guaranteed to be set
            args = self.args

            # Configure logging based on args
            configure_logging(getattr(args, 'verbose', False))

            # If --show-only-repo-files-chunks is specified, just show the chunks and exit
            if args.show_only_repo_files_chunks:
                # Find source files
                if args.file:
                    source_files = [args.file]
                    logger.warning(f"Using specific file: {args.file}")
                else:
                    source_files = find_files(args.directory)

                if not source_files:
                    logger.error(f"No source files found in directory: {args.directory}")
                    return 1

                # Display the file chunks without processing
                self._display_file_chunks(source_files)
                return 0

            # Normal processing mode
            processed_files = self.process_files(args)  # Pass the full args namespace

            if processed_files is not None:  # Check if None was returned due to critical error
                logger.info(f"\nSuccessfully processed {len(processed_files)} files.")
            else:
                logger.error("Processing failed due to a critical error.")
                return 1  # Indicate failure

            return 0
        except FileNotFoundError:
            # Error message already logged
            return 1
        except Exception as e:
            logger.exception(f"An unexpected error occurred in the main run loop: {e}")
            return 1

    def process_files(self, args: argparse.Namespace) -> Optional[List[str]]:
        """Process files using sonar-scanner.

        Args:
            args: Parsed command-line arguments namespace.

        Returns:
            List of files that were processed, or None on critical failure.
        """
        directory = args.directory

        if not os.path.isdir(directory):
            logger.error(f"Directory not found: {directory}")
            return None

        # Create sonar-project.properties file in the source directory
        self._create_sonar_properties_file(directory, args)

        # Get the name of the original source directory from environment variables
        # If not available, fall back to the name of the current directory
        source_dir_name = os.environ.get("ORIGINAL_SRC_DIR_NAME", os.path.basename(os.path.abspath(directory)))

        # Get project key (always use the name of the original directory)
        project_key = source_dir_name

        # Check if we should skip the scanner invocation
        skip_scanner = hasattr(args, 'skip_scanner') and args.skip_scanner

        if not skip_scanner:
            # Build sonar-scanner command
            cmd = ["sonar-scanner"]

            # Add project key (always use the name of the original directory)
            cmd.extend([f"-Dsonar.projectKey={project_key}"])

            # Add host URL if provided
            if hasattr(args, 'host_url') and args.host_url:
                cmd.extend([f"-Dsonar.host.url={args.host_url}"])

            # Add login token if provided
            if hasattr(args, 'login') and args.login:
                cmd.extend([f"-Dsonar.login={args.login}"])

            # Add sources if provided
            if hasattr(args, 'sources') and args.sources:
                cmd.extend([f"-Dsonar.sources={args.sources}"])
            else:
                # Default to the provided directory
                cmd.extend([f"-Dsonar.sources={directory}"])

            # Add exclusions if provided
            if hasattr(args, 'exclusions') and args.exclusions:
                cmd.extend([f"-Dsonar.exclusions={args.exclusions}"])

            # Run sonar-scanner
            logger.info(f"Running sonar-scanner on directory: {directory}")
            logger.info(f"Command: {' '.join(cmd)}")

            try:
                # Change to the directory before running sonar-scanner
                current_dir = os.getcwd()
                os.chdir(directory)

                # Run sonar-scanner
                result = subprocess.run(cmd, check=True, text=True, capture_output=True)

                # Log output
                logger.info("sonar-scanner output:")
                for line in result.stdout.splitlines():
                    logger.info(line)

                # Change back to original directory
                os.chdir(current_dir)

                logger.info("sonar-scanner completed successfully")
            except subprocess.CalledProcessError as e:
                logger.error(f"sonar-scanner failed with exit code {e.returncode}")
                logger.error(f"Error output: {e.stderr}")
                return None
            except Exception as e:
                logger.error(f"Error running sonar-scanner: {e}")
                return None
        else:
            logger.info(f"Skipping sonar-scanner invocation as requested by --skip-scanner parameter")
            logger.info(f"Will attempt to fetch measures for project: {project_key}")

        # Get SonarQube host URL
        host_url = args.host_url if hasattr(args, 'host_url') and args.host_url else "https://sonar.thefamouscat.com"

        # Get SonarQube token
        token = args.login if hasattr(args, 'login') and args.login else os.environ.get("SONAR_TOKEN", "")

        # Fetch measures and file_measures using SonarQubeClient
        logger.info(f"Fetching measures for project: {project_key} from {host_url}")
        client = SonarQubeClient(host_url, token)
        # Fetch project measures
        measures = client.fetch_measures(project_key)
        print(json.dumps(measures, indent=2))

        # Fetch file measures
        file_measures = client.fetch_file_measures(project_key)
        print(json.dumps(file_measures, indent=2))

        logger.info("Successfully fetched and displayed measures")

        return [directory]  # Return the directory as processed


def configure_logging(verbose: bool = False):
    """Configure logging for the sonar scanner processor.

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
    setup_logging(verbose, module_name="sonar_scanner")


def main() -> int:
    """Run the main script.

    Returns:
        Exit code (0 for success, non-zero for failure).
    """
    import argparse

    parser = argparse.ArgumentParser(description="Run sonar-scanner on the codebase")
    parser.add_argument("--verbose", "-v", action="store_true", help="Enable verbose logging")

    # Parse only the known args to avoid conflicts with the parent parser
    args, _ = parser.parse_known_args()

    # Configure logging
    configure_logging(args.verbose)

    processor = SonarScannerProcessor()
    return processor.run()


if __name__ == "__main__":
    sys.exit(main())
