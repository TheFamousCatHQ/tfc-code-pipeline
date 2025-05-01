"""Command-line interface for TFC Test Writer Aider.

This module provides the command-line interface for the TFC Test Writer Aider,
including argument parsing and execution of the main functionality.
"""

import argparse
import sys
from typing import Optional, Sequence

# Local application imports
from .main import main


def parse_args(args: Optional[Sequence[str]] = None) -> argparse.Namespace:
    """Parse command-line arguments.

    Args:
        args: Command line arguments. Defaults to None, which uses sys.argv.

    Returns:
        Parsed command-line arguments.
    """
    parser = argparse.ArgumentParser(description="TFC Test Writer Aider")
    parser.add_argument(
        "--build-only",
        action="store_true",
        help="Only build the Docker image without running the container"
    )
    parser.add_argument(
        "--run",
        action="store_true",
        help="Run the Docker container with the provided messages"
    )
    parser.add_argument(
        "--src",
        type=str,
        help="Directory to mount in the Docker container under /src"
    )
    parser.add_argument(
        "--cmd",
        type=str,
        choices=["explain_code", "write_tests", "find_bugs", "analyze_complexity"],
        default="explain_code",
        help="Command to run in the Docker container (explain_code, write_tests, find_bugs, or analyze_complexity)"
    )
    parser.add_argument(
        "-o", "--output",
        type=str,
        help="Path where the output will be saved (for commands that support it)"
    )

    # Add processor-specific arguments based on the command
    if args is None:
        args = sys.argv[1:]

    return parser.parse_args(args)


def cli() -> int:
    """Run the command-line interface.

    Parses command-line arguments and executes the main function.

    Returns:
        Exit code (0 for success, non-zero for failure).
    """
    args = parse_args()

    # Initialize processor_args dictionary if output is specified
    processor_args = {}
    if hasattr(args, 'output') and args.output is not None:
        processor_args['output'] = args.output

    return main(
        build_only=args.build_only, 
        run=args.run, 
        src=args.src, 
        cmd=args.cmd,
        processor_args=processor_args
    )


if __name__ == "__main__":
    exit(cli())
