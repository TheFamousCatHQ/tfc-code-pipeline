"""Command-line interface for TFC Test Writer Aider.

This module provides the command-line interface for the TFC Test Writer Aider,
including argument parsing and execution of the main functionality.
"""

import argparse
from typing import Any, Dict, List, Optional, Sequence, Union

# Local application imports
from tfc_test_writer_aider.main import main


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
        "--messages",
        type=str,
        default="Hello",
        help="Messages to pass to the Docker container"
    )
    return parser.parse_args(args)


def cli() -> int:
    """Run the command-line interface.

    Parses command-line arguments and executes the main function.

    Returns:
        Exit code (0 for success, non-zero for failure).
    """
    args = parse_args()
    return main(build_only=args.build_only, run=args.run, messages=args.messages)


if __name__ == "__main__":
    exit(cli())
