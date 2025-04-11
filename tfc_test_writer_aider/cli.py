"""Command-line interface for TFC Test Writer Aider."""

import argparse
from tfc_test_writer_aider.main import main


def parse_args():
    """Parse command-line arguments."""
    parser = argparse.ArgumentParser(description="TFC Test Writer Aider")
    parser.add_argument(
        "--build-only",
        action="store_true",
        help="Only build the Docker image without running the container"
    )
    return parser.parse_args()


def cli():
    """Run the command-line interface."""
    args = parse_args()
    return main(build_only=args.build_only)


if __name__ == "__main__":
    exit(cli())
