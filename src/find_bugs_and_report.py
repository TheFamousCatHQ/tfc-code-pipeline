#!/usr/bin/env python3
"""
Executable script to run the bug analyzer (natively, not via Docker) and display issues on a single line.

Usage:
    poetry run find-bugs-and-report [--commit COMMIT] [--working-tree] [--branch-diff BRANCH] [--remote-diff] [--directory DIRECTORY] [--output OUTPUT_FILE]
                                    [--severity-threshold {high,medium,low}] [--confidence-threshold {high,medium,low}]

This script runs the bug analyzer using the local Python modules, parses the output XML, and shows each bug on a single line.
It can also break the build if issues with severity at or above the specified threshold and confidence at or above the specified threshold are found.
"""

import argparse
import os
import sys
import threading
import time
import xml.etree.ElementTree as ET
from pathlib import Path
from typing import Optional, List, Dict
import logging

from colorama import init, Fore, Style

# Import the processors directly
from bug_analyzer import BugAnalyzerProcessor

DEFAULT_ENV_FILE = ".env"

init(autoreset=True)

SPINNER_CHARS = ["|", "/", "-", "\\"]

# Define severity and confidence levels for comparison
SEVERITY_LEVELS = {"high": 3, "medium": 2, "low": 1}
CONFIDENCE_LEVELS = {"high": 3, "medium": 2, "low": 1}


def run_bug_analyzer_local(commit: Optional[str], working_tree: bool, output: str, directory: str = "/src", debug: bool = False, branch_diff: Optional[str] = None, remote_diff: bool = False) -> int:
    """
    Run the bug analyzer using the local Python module and write output to the specified file.
    Show a spinner while waiting.

    Args:
        commit: Commit ID to analyze
        working_tree: Whether to analyze working tree changes
        output: Output file path
        directory: Directory to analyze (default: /src)
        debug: Whether to enable debug mode
        branch_diff: Branch to compare with current branch (e.g., 'main')
        remote_diff: Whether to analyze diff between local branch and its remote counterpart
    """
    spinner_running = True
    spinner_done = False
    spinner_exception = [None]

    def spinner():
        idx = 0
        print("\nRunning bug analyzer... ", end="", flush=True)
        while spinner_running:
            print(f"{Fore.CYAN}{SPINNER_CHARS[idx % len(SPINNER_CHARS)]}\rRunning bug analyzer... ", end="", flush=True)
            idx += 1
            time.sleep(0.1)
        print(" " * 40 + "\r", end="", flush=True)  # Clear spinner
        if spinner_done:
            print(f"{Fore.GREEN}✔ Bug analysis complete!\n", flush=True)

    t = threading.Thread(target=spinner)
    t.start()
    try:
        # Prepare args for BugAnalyzerProcessor
        args = [
            "--directory", directory,
            "--output", output
        ]
        if commit:
            args.extend(["--commit", commit])
        if working_tree:
            args.append("--working-tree")
        if branch_diff:
            args.extend(["--branch-diff", branch_diff])
        if remote_diff:
            args.append("--remote-diff")
        if debug:
            args.append("--debug")
        processor = BugAnalyzerProcessor()
        # Patch sys.argv for argparse in processor
        sys_argv_backup = sys.argv
        sys.argv = ["bug_analyzer"] + args
        try:
            processor.run()
            retcode = 0
        finally:
            sys.argv = sys_argv_backup
    except Exception as e:
        spinner_exception[0] = e
        retcode = 1
    finally:
        spinner_running = False
        spinner_done = True
        t.join()
    return retcode


def parse_and_report_bugs(xml_path: str, severity_threshold: str, confidence_threshold: str) -> int:
    """
    Parse the bug analysis report and display each issue on a single line.
    Return non-zero exit code if issues with severity at or above the specified threshold and
    confidence at or above the specified threshold are found.

    Args:
        xml_path: Path to the bug analysis report XML file
        severity_threshold: Severity threshold (high, medium, low)
        confidence_threshold: Confidence threshold (high, medium, low)

    Returns:
        0 if no issues meeting the threshold criteria are found, 1 otherwise
    """
    if not Path(xml_path).exists():
        print(f"Bug analysis report not found: {xml_path}", file=sys.stderr)
        return 1

    tree = ET.parse(xml_path)
    root = tree.getroot()
    bugs_elem = root.find("bugs")

    if bugs_elem is None or not list(bugs_elem):
        print(f"{Fore.GREEN}No bugs found in the analysis report.{Style.RESET_ALL}")
        return 0

    bugs = bugs_elem.findall("bug")
    print(f"{Fore.GREEN}Found {len(bugs)} bug(s) in the analysis report.{Style.RESET_ALL}")

    # Convert thresholds to numeric values for comparison
    severity_threshold_value = SEVERITY_LEVELS.get(severity_threshold.lower(), 0)
    confidence_threshold_value = CONFIDENCE_LEVELS.get(confidence_threshold.lower(), 0)

    # Track if any issues exceed thresholds
    threshold_exceeded = False

    # Display each bug on a single line
    for bug in bugs:
        file_path = bug.findtext("file_path", "<unknown>")
        line_number = bug.findtext("line_number", "<unknown>")
        description = bug.findtext("description", "<no description>")
        severity = bug.findtext("severity", "<unknown>").lower()
        confidence = bug.findtext("confidence", "<unknown>").lower()

        # Determine if this bug exceeds thresholds
        severity_value = SEVERITY_LEVELS.get(severity, 0)
        confidence_value = CONFIDENCE_LEVELS.get(confidence, 0)
        exceeds_threshold = (severity_value >= severity_threshold_value and 
                             confidence_value >= confidence_threshold_value)

        if exceeds_threshold:
            threshold_exceeded = True
            prefix = f"{Fore.RED}[THRESHOLD EXCEEDED]"
        else:
            prefix = f"{Fore.YELLOW}[INFO]"

        # Format severity and confidence with colors
        if severity in SEVERITY_LEVELS:
            if severity == "high":
                severity_display = f"{Fore.RED}{severity.upper()}"
            elif severity == "medium":
                severity_display = f"{Fore.YELLOW}{severity.upper()}"
            else:
                severity_display = f"{Fore.CYAN}{severity.upper()}"
        else:
            severity_display = f"{Fore.WHITE}{severity}"

        if confidence in CONFIDENCE_LEVELS:
            if confidence == "high":
                confidence_display = f"{Fore.GREEN}{confidence.upper()}"
            elif confidence == "medium":
                confidence_display = f"{Fore.YELLOW}{confidence.upper()}"
            else:
                confidence_display = f"{Fore.RED}{confidence.upper()}"
        else:
            confidence_display = f"{Fore.WHITE}{confidence}"

        # Print the bug on a single line
        print(f"{prefix} {file_path}:{line_number} - {description} [Severity: {severity_display}{Style.RESET_ALL}, Confidence: {confidence_display}{Style.RESET_ALL}]")

    # Return non-zero exit code if any issues exceed thresholds
    if threshold_exceeded:
        print(f"\n{Fore.RED}Issues found that exceed specified thresholds. Build failed.{Style.RESET_ALL}")
        return 1

    return 0


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Run the bug analyzer (natively) and display issues on a single line."
    )
    parser.add_argument(
        "--commit",
        type=str,
        default=None,
        help="Commit ID to analyze (default: HEAD)"
    )
    parser.add_argument(
        "--working-tree",
        action="store_true",
        help="Analyze diff between working tree and HEAD instead of a specific commit"
    )
    parser.add_argument(
        "--branch-diff",
        type=str,
        help="Analyze diff between current branch and specified branch (e.g., 'main')"
    )
    parser.add_argument(
        "--remote-diff",
        action="store_true",
        help="Analyze diff between local branch and its remote counterpart"
    )
    parser.add_argument(
        "--directory",
        type=str,
        default="/src",
        help="Directory to analyze (default: /src)"
    )
    parser.add_argument(
        "--output",
        type=str,
        default="bug_analysis_report.xml",
        help="Output file path for the bug analysis report (default: bug_analysis_report.xml)"
    )
    parser.add_argument(
        "--severity-threshold",
        type=str,
        choices=["high", "medium", "low"],
        default="high",
        help="Severity threshold at or above which to break the build (default: high)"
    )
    parser.add_argument(
        "--confidence-threshold",
        type=str,
        choices=["high", "medium", "low"],
        default="high",
        help="Confidence threshold at or above which to break the build (default: high)"
    )
    parser.add_argument(
        "--debug",
        action="store_true",
        help="Pass --debug to all processors and print debug info"
    )
    args = parser.parse_args()

    # Set logging level based on --debug
    if args.debug:
        logging.basicConfig(level=logging.INFO)
    else:
        logging.basicConfig(level=logging.CRITICAL)
        # Silence noisy loggers from dependencies
        for noisy_logger in [
            "root", "tfc-code-pipeline", "tfc-code-pipeline.bug_analyzer", "schema_cat", "httpx", "urllib3", "asyncio", "openai", "pydantic", "requests"
        ]:
            logging.getLogger(noisy_logger).setLevel(logging.CRITICAL)

    try:
        # Run the bug analyzer natively
        ret = run_bug_analyzer_local(args.commit, args.working_tree, args.output, args.directory, debug=args.debug, branch_diff=args.branch_diff, remote_diff=args.remote_diff)
        if ret != 0:
            print("Bug analyzer failed. Exiting.", file=sys.stderr)
            sys.exit(ret)

        # Parse and report bugs
        ret = parse_and_report_bugs(args.output, args.severity_threshold, args.confidence_threshold)

        # Delete the bug analysis report file if it exists
        try:
            if os.path.exists(args.output):
                os.remove(args.output)
                if args.debug:
                    print(f"[DEBUG] Deleted bug analysis report: {args.output}")
        except Exception as e:
            print(f"[DEBUG] Error deleting bug analysis report: {e}")

        # Exit with the return code from parse_and_report_bugs
        sys.exit(ret)
    except KeyboardInterrupt:
        print("Exiting....")
        if args.debug:
            print("KeyboardInterrupt: Exiting on user request.", file=sys.stderr)
        sys.exit(130)


if __name__ == "__main__":
    main()
