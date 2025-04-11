"""Command-line interface for TFC Test Writer Aider."""

import argparse
from tfc_test_writer_aider.main import main


def parse_args():
    """Parse command-line arguments."""
    parser = argparse.ArgumentParser(description="TFC Test Writer Aider")
    return parser.parse_args()


def cli():
    """Run the command-line interface."""
    parse_args()
    return main()


if __name__ == "__main__":
    exit(cli())
