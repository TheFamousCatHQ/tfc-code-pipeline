"""Command-line interface for TFC Test Writer Aider.

This module provides the command-line interface for the TFC Test Writer Aider,
including argument parsing and execution of the main functionality.
"""

import argparse
import sys
from typing import Optional, Sequence, List

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

    # Add processor-specific arguments based on the command
    if args is None:
        args = sys.argv[1:]

    # Convert args to list if it's not already
    args_list = list(args)

    # Find the index of --cmd if it exists
    cmd_index = -1
    cmd_value = "explain_code"  # Default value
    for i, arg in enumerate(args_list):
        if arg == "--cmd" and i + 1 < len(args_list):
            cmd_index = i
            cmd_value = args_list[i + 1]
            break
        elif arg.startswith("--cmd="):
            cmd_index = i
            cmd_value = arg.split("=", 1)[1]
            break

    # Add processor-specific arguments
    if cmd_value == "analyze_complexity":
        parser.add_argument(
            "-o", "--output",
            type=str,
            help="Path where the master complexity report will be saved"
        )

    return parser.parse_args(args)


def cli() -> int:
    """Run the command-line interface.

    Parses command-line arguments and executes the main function.

    Returns:
        Exit code (0 for success, non-zero for failure).
    """
    args = parse_args()
    # Note: messages parameter is parsed but not used in the main function

    # Collect processor-specific arguments
    processor_args = {}
    if args.cmd == "analyze_complexity" and hasattr(args, "output") and args.output:
        processor_args["output"] = args.output

    return main(build_only=args.build_only, run=args.run, src=args.src, cmd=args.cmd, processor_args=processor_args)


if __name__ == "__main__":
    exit(cli())
