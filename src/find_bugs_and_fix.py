#!/usr/bin/env python3
"""
Executable script to run the bug analyzer (natively, not via Docker) and interactively display suggested bug fixes.

Usage:
    poetry run find-bugs-and-fix [--commit COMMIT] [--working-tree] [--directory DIRECTORY] [--output OUTPUT_FILE]

This script runs the bug analyzer using the local Python modules, parses the output XML, and shows each bug fix suggestion
one-by-one on the command line, pausing for user input between each.
"""

import argparse
import os
import re
import sys
import tempfile
import textwrap
import threading
import time
import xml.etree.ElementTree as ET
from pathlib import Path
from typing import Optional, List

from colorama import init, Fore, Style

# Import the processors directly
from bug_analyzer import BugAnalyzerProcessor
from tfc_code_pipeline.fix_bugs import FixBugsProcessor

DEFAULT_ENV_FILE = ".env"

init(autoreset=True)

SPINNER_CHARS = ["|", "/", "-", "\\"]


def run_bug_analyzer_local(commit: Optional[str], working_tree: bool, output: str, directory: str = os.getcwd(), debug: bool = False) -> int:
    """
    Run the bug analyzer using the local Python module and write output to the specified file.
    Show a spinner while waiting.

    Args:
        commit: Commit ID to analyze
        working_tree: Whether to analyze working tree changes
        output: Output file path
        directory: Directory to analyze (default: current working directory)
        debug: Whether to enable debug mode
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


def print_bug(idx: int, total: int, bug: ET.Element) -> None:
    BOX_WIDTH = 66
    INNER_WIDTH = BOX_WIDTH - 2
    LABEL = Style.BRIGHT + Fore.YELLOW
    VALUE = Style.NORMAL + Fore.WHITE
    SEVERITY_COLORS = {
        "high": Fore.RED + Style.BRIGHT,
        "medium": Fore.YELLOW + Style.BRIGHT,
        "low": Fore.CYAN + Style.BRIGHT,
    }
    CONFIDENCE_COLORS = {
        "high": Fore.GREEN + Style.BRIGHT,
        "medium": Fore.YELLOW + Style.BRIGHT,
        "low": Fore.RED + Style.BRIGHT,
    }
    file_path = bug.findtext("file_path", "<unknown>")
    line_number = bug.findtext("line_number", "<unknown>")
    description = bug.findtext("description", "<no description>")
    severity = bug.findtext("severity", "<unknown>").lower()
    confidence = bug.findtext("confidence", "<unknown>").lower()
    suggested_fix = bug.findtext("suggested_fix", "<no suggestion>")
    code_snippet = bug.findtext("code_snippet", "")
    severity_color = SEVERITY_COLORS.get(severity, Fore.WHITE + Style.BRIGHT)
    confidence_color = CONFIDENCE_COLORS.get(confidence, Fore.WHITE + Style.BRIGHT)

    def _strip_ansi(s: str) -> str:
        return re.sub(r'\x1b\[[0-9;]*m', '', s)

    def box_line(content: str = "", color: str = "") -> str:
        pad_len = INNER_WIDTH - len(_strip_ansi(content))
        return f"{Style.BRIGHT}{Fore.MAGENTA}┃{Style.RESET_ALL}{color}{content}{' ' * pad_len}{Style.RESET_ALL}{Style.BRIGHT}{Fore.MAGENTA}┃{Style.RESET_ALL}"

    def box_wrap(label: str, value: str, color: str = "", label_color: str = LABEL, value_color: str = VALUE) -> None:
        label_str = f"{label_color}{label}{value_color}"
        label_len = len(_strip_ansi(label))
        wrap_width = INNER_WIDTH - label_len
        wrapped = textwrap.wrap(value, width=wrap_width)
        if not wrapped:
            print(box_line(label_str, color))
            return
        print(box_line(label_str + wrapped[0], color))
        for line in wrapped[1:]:
            print(box_line(' ' * label_len + line, color))

    print(f"{Style.BRIGHT}{Fore.MAGENTA}┏{'━' * (BOX_WIDTH - 2)}┓{Style.RESET_ALL}")
    bug_num = f"  Bug {idx}/{total}"
    print(box_line(bug_num, Style.BRIGHT + Fore.CYAN))
    print(f"{Style.BRIGHT}{Fore.MAGENTA}┣{'━' * (BOX_WIDTH - 2)}{Style.RESET_ALL}")
    box_wrap("File:        ", file_path)
    box_wrap("Line:        ", line_number)
    box_wrap("Severity:    ", severity.capitalize(), severity_color)
    box_wrap("Confidence:  ", confidence.capitalize(), confidence_color)
    box_wrap("Description: ", description)
    box_wrap("Suggested fix:", suggested_fix)
    if code_snippet:
        print(box_line(f"{LABEL}Code snippet:{Style.RESET_ALL}"))
        for line in code_snippet.splitlines():
            for wrapped in textwrap.wrap(line, width=INNER_WIDTH):
                print(box_line(f"{Fore.BLUE}{wrapped}{Style.RESET_ALL}"))
    print(f"{Style.BRIGHT}{Fore.MAGENTA}┗{'━' * (BOX_WIDTH - 2)}┛{Style.RESET_ALL}")


def create_single_bug_xml(bug: ET.Element, original_xml_path: str) -> str:
    tree = ET.parse(original_xml_path)
    root = tree.getroot()
    commit_id = root.findtext("commit_id", "HEAD")
    timestamp = root.findtext("timestamp", "")
    affected_files_elem = root.find("affected_files")
    summary = root.findtext("summary", None)
    bug_report = ET.Element("bug_analysis_report")
    ET.SubElement(bug_report, "commit_id").text = commit_id
    ET.SubElement(bug_report, "timestamp").text = timestamp
    affected_files = ET.SubElement(bug_report, "affected_files")
    if affected_files_elem is not None:
        for file_elem in affected_files_elem.findall("file"):
            ET.SubElement(affected_files, "file").text = file_elem.text
    bugs_elem = ET.SubElement(bug_report, "bugs")
    bugs_elem.append(bug)
    if summary:
        ET.SubElement(bug_report, "summary").text = summary
    tmp = tempfile.NamedTemporaryFile(delete=False, suffix="_single_bug.xml", mode="w", encoding="utf-8", dir=os.getcwd())
    tmp.write('<?xml version="1.0" encoding="UTF-8"?>\n')
    xml_str = ET.tostring(bug_report, encoding="unicode")
    tmp.write(xml_str)
    tmp.close()
    return tmp.name


def apply_fix_local(bug: ET.Element, auto_commit: bool, original_xml_path: str, debug: bool = False) -> None:
    single_bug_xml = create_single_bug_xml(bug, original_xml_path)
    try:
        args = [
            "--single-bug-xml", single_bug_xml
        ]
        if auto_commit:
            args.append("--auto-commit")
        if debug:
            args.append("--debug")
        processor = FixBugsProcessor()
        sys_argv_backup = sys.argv
        sys.argv = ["fix_bugs"] + args
        try:
            processor.run()
        finally:
            sys.argv = sys_argv_backup
    finally:
        try:
            os.unlink(single_bug_xml)
        except Exception:
            pass


def prompt_apply_fix(bug: ET.Element, original_xml_path: str, debug: bool = False) -> None:
    while True:
        answer = input(f"{Style.BRIGHT}{Fore.YELLOW}Apply this fix? [Y/n/a]: {Style.RESET_ALL}").strip().lower()
        if answer == "" or answer == "y":
            apply_fix_local(bug, auto_commit=False, original_xml_path=original_xml_path, debug=debug)
            break
        elif answer == "n":
            break
        elif answer == "a":
            apply_fix_local(bug, auto_commit=True, original_xml_path=original_xml_path, debug=debug)
            break
        else:
            print(f"{Fore.RED}Please answer 'Y' (yes), 'n' (no), or 'a' (yes-with-auto-commit).{Style.RESET_ALL}")


def parse_and_show_fixes(xml_path: str, debug: bool = False) -> None:
    if not Path(xml_path).exists():
        print(f"Bug analysis report not found: {xml_path}", file=sys.stderr)
        sys.exit(1)
    tree = ET.parse(xml_path)
    root = tree.getroot()
    bugs_elem = root.find("bugs")
    if bugs_elem is None or not list(bugs_elem):
        print(f"{Fore.GREEN}No bugs found in the analysis report.{Style.RESET_ALL}")
        return
    bugs = bugs_elem.findall("bug")
    print(f"{Fore.GREEN}Found {len(bugs)} bug(s) in the analysis report.\n{Style.RESET_ALL}")
    for idx, bug in enumerate(bugs, 1):
        print_bug(idx, len(bugs), bug)
        prompt_apply_fix(bug, xml_path, debug=debug)


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Run the bug analyzer (natively) and interactively show suggested bug fixes."
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
        "--directory",
        type=str,
        default=os.getcwd(),
        help="Directory to analyze (default: current working directory)"
    )
    parser.add_argument(
        "--output",
        type=str,
        default="bug_analysis_report.xml",
        help="Output file path for the bug analysis report (default: bug_analysis_report.xml)"
    )
    parser.add_argument(
        "--debug",
        action="store_true",
        help="Pass --debug to all processors and print debug info"
    )
    args = parser.parse_args()

    # Run the bug analyzer natively
    ret = run_bug_analyzer_local(args.commit, args.working_tree, args.output, args.directory, debug=args.debug)
    if ret != 0:
        print("Bug analyzer failed. Exiting.", file=sys.stderr)
        sys.exit(ret)

    # Parse and show bug fixes
    parse_and_show_fixes(args.output, debug=args.debug)

    # Delete the bug analysis report file if it exists
    try:
        if os.path.exists(args.output):
            os.remove(args.output)
            if args.debug:
                print(f"[DEBUG] Deleted bug analysis report: {args.output}")
    except Exception as e:
        print(f"[DEBUG] Error deleting bug analysis report: {e}")


if __name__ == "__main__":
    main() 
