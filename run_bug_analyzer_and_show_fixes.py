#!/usr/bin/env python3
"""
Executable script to run the bug analyzer (via Docker) and interactively display suggested bug fixes.

Usage:
    python run_bug_analyzer_and_show_fixes.py [--commit COMMIT] [--working-tree] [--output OUTPUT_FILE]

This script runs the bug analyzer using the Docker image, parses the output XML, and shows each bug fix suggestion
one-by-one on the command line, pausing for user input between each.
"""

import argparse
import os
import re
import subprocess
import sys
import tempfile
import textwrap
import threading
import time
import xml.etree.ElementTree as ET
from pathlib import Path
from typing import Optional, List

from colorama import init, Fore, Style

IMAGE_NAME = "tfccodepipeline/app:latest"
DEFAULT_ENV_FILE = ".env"

init(autoreset=True)

SPINNER_CHARS = ["|", "/", "-", "\\"]


def read_env_file(env_file: str) -> List[str]:
    """
    Read environment variables from a .env file and return as a list of '-e KEY=VALUE' flags for Docker.
    """
    env_flags = []
    if os.path.isfile(env_file):
        with open(env_file, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if not line or line.startswith("#"):
                    continue
                if "=" in line:
                    key, value = line.split("=", 1)
                    env_flags.extend(["-e", f"{key}={value}"])
    return env_flags


def run_bug_analyzer_docker(
        commit: Optional[str],
        working_tree: bool,
        output: str,
        env_file: str,
        debug: bool = False
) -> int:
    """
    Run the bug analyzer using the Docker image and write output to the specified file.
    Suppress all logging output from the container.
    Show a spinner while waiting.
    """
    src_dir = os.getcwd()
    env_flags = read_env_file(env_file)
    env_flags.extend(["-e", f"ORIGINAL_SRC_DIR_NAME={os.path.basename(src_dir)}"])
    cmd = [
        "docker", "run", "--rm", "-i",  # no -t to avoid color issues in logs
        *env_flags,
        "-v", f"{src_dir}:/src",
        "--entrypoint", "bug-analyzer",
        IMAGE_NAME,
        "--directory", "/src",
        "--output", output
    ]
    if commit:
        cmd.extend(["--commit", commit])
    if working_tree:
        cmd.append("--working-tree")
    if debug:
        cmd.append("--debug")
        print(f"[DEBUG] Running Docker command: {' '.join(cmd)}")

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
        # Use Popen and poll so spinner can update
        process = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
        while process.poll() is None:
            time.sleep(0.1)
        stdout, stderr = process.communicate()
        retcode = process.returncode
    except Exception as e:
        spinner_exception[0] = e
        retcode = 1
        stdout, stderr = '', str(e)
    finally:
        spinner_running = False
        spinner_done = True
        t.join()
    if retcode != 0:
        print(stderr, file=sys.stderr)
    return retcode


def print_bug(idx: int, total: int, bug: ET.Element) -> None:
    """
    Pretty-print a bug with colors and bold labels, with a perfectly aligned and wrapped box.
    """
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
        # Only show the label on the first line, indent wrapped lines to align after the label
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

    # Top border
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
    # Bottom border
    print(f"{Style.BRIGHT}{Fore.MAGENTA}┗{'━' * (BOX_WIDTH - 2)}┛{Style.RESET_ALL}")


def create_single_bug_xml(bug: ET.Element, original_xml_path: str) -> str:
    """
    Create a temporary XML file containing only this bug, in the same format as the main report.
    Returns the path to the temp file.
    """
    # Parse the original XML to get commit_id, timestamp, affected_files, summary
    tree = ET.parse(original_xml_path)
    root = tree.getroot()
    commit_id = root.findtext("commit_id", "HEAD")
    timestamp = root.findtext("timestamp", "")
    affected_files_elem = root.find("affected_files")
    summary = root.findtext("summary", None)
    # Build new XML
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
    # Write to temp file in the current working directory so Docker can see it
    tmp = tempfile.NamedTemporaryFile(delete=False, suffix="_single_bug.xml", mode="w", encoding="utf-8",
                                      dir=os.getcwd())
    tmp.write('<?xml version="1.0" encoding="UTF-8"?>\n')
    xml_str = ET.tostring(bug_report, encoding="unicode")
    tmp.write(xml_str)
    tmp.close()
    return tmp.name


def apply_fix(bug: ET.Element, auto_commit: bool, original_xml_path: str, env_file: str, debug: bool = False) -> None:
    """
    Call fix_bugs in Docker with --single-bug-xml /src/<filename>.
    If auto_commit is True, also pass --auto-commit.
    Print debug info about what is executed and file handling.
    """
    single_bug_xml = create_single_bug_xml(bug, original_xml_path)
    single_bug_xml_name = os.path.basename(single_bug_xml)
    container_xml_path = f"/src/{single_bug_xml_name}"
    print(f"[DEBUG] Created single bug XML: {single_bug_xml} (container path: {container_xml_path})")
    if debug:
        print(f"[DEBUG] Content of {single_bug_xml}:")
        try:
            with open(single_bug_xml, "r", encoding="utf-8") as f:
                print(f.read())
        except Exception as e:
            print(f"[DEBUG] Error reading {single_bug_xml}: {e}")
        print(f"[DEBUG] End of {single_bug_xml}")
    src_dir = os.getcwd()
    env_flags = read_env_file(env_file)
    env_flags.extend(["-e", f"ORIGINAL_SRC_DIR_NAME={os.path.basename(src_dir)}"])
    # Print all AIDER_ environment variables
    for k, v in os.environ.items():
        if k.startswith("AIDER_"):
            print(f"[DEBUG] {k}: {v}")
    cmd = [
        "docker", "run", "--rm", "-i",
        *env_flags,
        "-v", f"{src_dir}:/src",
        "-w", "/src",  # Ensure working directory is /src for git
        "--entrypoint", "fix-bugs",
        IMAGE_NAME,
        "--single-bug-xml", container_xml_path
    ]
    if auto_commit:
        cmd.append("--auto-commit")
    if debug:
        cmd.append("--debug")
        print(f"[DEBUG] Running Docker command: {' '.join(cmd)}")
    print(f"\n{Fore.CYAN}Applying fix using fix_bugs...{Style.RESET_ALL}")
    result = subprocess.run(cmd, capture_output=True, text=True)
    print(f"[DEBUG] Docker return code: {result.returncode}")
    print(f"[DEBUG] Docker stdout:\n{result.stdout}")
    if result.stderr:
        print(f"[DEBUG] Docker stderr:\n{result.stderr}")
    if result.returncode != 0:
        print(result.stderr, file=sys.stderr)
    # Optionally, remove the temp file
    try:
        os.unlink(single_bug_xml)
        print(f"[DEBUG] Deleted temp file: {single_bug_xml}")
    except Exception as e:
        print(f"[DEBUG] Error deleting temp file: {e}")


def prompt_apply_fix(bug: ET.Element, original_xml_path: str, env_file: str, debug: bool = False) -> None:
    """
    Prompt the user whether to apply the fix, with Y/n/a options.
    """
    while True:
        answer = input(f"{Style.BRIGHT}{Fore.YELLOW}Apply this fix? [Y/n/a]: {Style.RESET_ALL}").strip().lower()
        if answer == "" or answer == "y":
            apply_fix(bug, auto_commit=False, original_xml_path=original_xml_path, env_file=env_file, debug=debug)
            break
        elif answer == "n":
            break
        elif answer == "a":
            apply_fix(bug, auto_commit=True, original_xml_path=original_xml_path, env_file=env_file, debug=debug)
            break
        else:
            print(f"{Fore.RED}Please answer 'Y' (yes), 'n' (no), or 'a' (yes-with-auto-commit).{Style.RESET_ALL}")


def parse_and_show_fixes(xml_path: str, env_file: str, debug: bool = False) -> None:
    """
    Parse the bug analysis XML and show each bug fix suggestion interactively.
    """
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
        prompt_apply_fix(bug, xml_path, env_file, debug=debug)


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Run the bug analyzer (via Docker) and interactively show suggested bug fixes."
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
        "--output",
        type=str,
        default="bug_analysis_report.xml",
        help="Output file path for the bug analysis report (default: bug_analysis_report.xml)"
    )
    parser.add_argument(
        "--env-file",
        type=str,
        default=DEFAULT_ENV_FILE,
        help="Path to .env file to load environment variables (default: .env)"
    )
    parser.add_argument(
        "--debug",
        action="store_true",
        help="Pass --debug to all Docker commands and print debug info"
    )
    args = parser.parse_args()

    # Run the bug analyzer in Docker
    ret = run_bug_analyzer_docker(args.commit, args.working_tree, args.output, args.env_file, debug=args.debug)
    if ret != 0:
        print("Bug analyzer failed. Exiting.", file=sys.stderr)
        sys.exit(ret)

    # Parse and show bug fixes
    parse_and_show_fixes(args.output, args.env_file, debug=args.debug)


if __name__ == "__main__":
    main()
