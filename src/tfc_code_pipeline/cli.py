"""Command-line interface for TFC Test Writer Aider.

This module provides the command-line interface for the TFC Test Writer Aider,
including argument parsing and execution of the main functionality.
"""

import argparse
import importlib
import sys
from typing import Optional, Sequence, Dict

from code_processor import CodeProcessor  # Import base class
from logging_utils import get_logger
# Local application imports
from .main import main

# Set up logging
logger = get_logger()

# Map command names to processor module and class names
PROCESSOR_MAP: Dict[str, Dict[str, str]] = {
    "explain_code": {"module": "explain_code", "class": "ExplainCodeProcessor"},
    "write_tests": {"module": "write_tests", "class": "WriteTestsProcessor"},
    "find_bugs": {"module": "find_bugs", "class": "FindBugsProcessor"},
    "analyze_complexity": {"module": "complexity_analyzer", "class": "ComplexityAnalyzerProcessor"},
    "sonar_scan": {"module": "sonar_scanner", "class": "SonarScannerProcessor"},
    "bug_analyzer": {"module": "bug_analyzer", "class": "BugAnalyzerProcessor"},
    "fix_bugs": {"module": "tfc_code_pipeline.fix_bugs", "class": "FixBugsProcessor"},
}


def get_processor_instance(cmd: Optional[str]) -> Optional[CodeProcessor]:
    """Dynamically import and instantiate the appropriate CodeProcessor based on cmd."""
    if not cmd or cmd not in PROCESSOR_MAP:
        return None

    proc_info = PROCESSOR_MAP[cmd]
    module_name = proc_info["module"]
    class_name = proc_info["class"]

    try:
        # Dynamically import the module
        # Assume modules are directly importable (e.g., installed or in sys.path)
        module = importlib.import_module(module_name)
        # Get the class from the imported module
        ProcessorClass = getattr(module, class_name)
        # Instantiate the processor (will parse args later if needed)
        # Pass None initially, args will be parsed fully later by the main parser
        processor = ProcessorClass(args=None)
        if not isinstance(processor, CodeProcessor):
            raise TypeError(f"{class_name} is not a subclass of CodeProcessor")
        return processor
    except (ImportError, AttributeError, TypeError) as e:
        logger.error(f"Error loading processor for command '{cmd}': {e}")
        return None


def parse_args(args: Optional[Sequence[str]] = None) -> argparse.Namespace:
    """Parse command-line arguments, including processor-specific args.

    Args:
        args: Command line arguments. Defaults to None, which uses sys.argv[1:].

    Returns:
        Parsed command-line arguments (Namespace).
    """
    if args is None:
        args = sys.argv[1:]

    # --- Pre-parse to find --cmd --- #
    pre_parser = argparse.ArgumentParser(add_help=False)  # Don't interfere with main help
    pre_parser.add_argument("--cmd", type=str)
    # Ignore other args for now
    known_pre_args, _ = pre_parser.parse_known_args(args)
    cmd = known_pre_args.cmd

    # --- Get processor instance to add its args --- #
    processor = get_processor_instance(cmd)

    # --- Build the main parser --- #
    parser = argparse.ArgumentParser(
        description="TFC Code Pipeline - Build/Run code processors in Docker.",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter  # Show defaults
    )
    # Add main arguments
    parser.add_argument(
        "--build-only",
        action="store_true",
        help="Only build the Docker image, do not run."
    )
    parser.add_argument(
        "--skip-build",
        action="store_true",
        help="Skip building the Docker image, only run the command."
    )
    parser.add_argument(
        "--run",
        action="store_true",
        help="Run the command in the Docker container (requires --src and --cmd)."
    )
    parser.add_argument(
        "--src",
        type=str,
        help="Host directory containing the source code to process."
    )
    parser.add_argument(
        "--cmd",
        type=str,
        choices=list(PROCESSOR_MAP.keys()),
        required=False,  # Not required if --generate-dockerfile is used
        help="Command (processor) to run. Available: explain_code, write_tests, find_bugs, analyze_complexity, sonar_scan, bug_analyzer, fix_bugs (run bug_analyzer, then feed XML to aider to fix bugs)."
    )
    parser.add_argument(
        "--generate-dockerfile",
        action="store_true",
        help="Only generate the Dockerfile without building or running."
    )
    parser.add_argument(
        "--platform",
        type=str,
        help="Platform to build the Docker image for (e.g., linux/amd64, linux/arm64)."
    )
    # Add a group for processor-specific arguments for clarity in help message
    processor_group = parser.add_argument_group(f'{cmd} arguments' if processor else 'processor arguments')

    # --- Add processor-specific arguments --- #
    if processor:
        # Call the processor's method to add its specific arguments to the group
        processor.add_arguments(processor_group)  # Pass the group
    else:
        # Add a note if processor couldn't be loaded
        processor_group.description = "Arguments for the selected processor will appear here if --cmd is valid."
        if cmd:
            logger.warning(f"Could not load arguments for processor '{cmd}'. Help message may be incomplete.")

    # --- Parse all arguments together --- #
    parsed_args = parser.parse_args(args)

    # --- Post-parse validation --- #
    if parsed_args.run and not parsed_args.src:
        parser.error("--src is required when using --run")
    # --cmd is already required by the parser

    return parsed_args


def cli() -> int:
    """Run the command-line interface.

    Parses command-line arguments and executes the main function.

    Returns:
        Exit code (0 for success, non-zero for failure).
    """
    args = parse_args()
    # Pass the full args namespace to main
    return main(args)


if __name__ == "__main__":
    sys.exit(cli())
