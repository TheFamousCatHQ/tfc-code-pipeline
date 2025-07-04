#!/usr/bin/env python3
"""
Script to analyze bugs in code changes using OpenRouter.

This script can operate in four modes:
1. Commit mode: Takes the diff of a commit, plus the full source of all affected files.
2. Working tree mode: Takes the diff between the working tree and HEAD, plus the full source of all affected files.
3. Branch diff mode: Takes the diff between the current branch and a specified branch, plus the full source of all affected files.
4. Remote diff mode: Takes the diff between the local branch and its remote counterpart, plus the full source of all affected files.

It feeds the diff and file contents to OpenRouter and asks for a bug analysis. 
The output is in a standardized XML format.
"""

import argparse
import asyncio
import json
import os
import subprocess
import xml.etree.ElementTree as ET
from datetime import datetime
from typing import Dict, List, Any, Optional

import schema_cat
from pydantic import BaseModel, Field

from code_processor import CodeProcessor
from logging_utils import get_logger

# Set up logging
logger = get_logger("tfc-code-pipeline.bug_analyzer")


def force_debug_logging(logger):
    logger.setLevel('DEBUG')
    # Set all handlers for this logger and its parents to DEBUG
    current = logger
    while current:
        for handler in current.handlers:
            handler.setLevel('DEBUG')
        if not getattr(current, 'propagate', True):
            break
        current = getattr(current, 'parent', None)


class BugAnalysis(BaseModel):
    """Model for bug analysis results."""
    file_path: str = Field(..., description="Path to the file containing the bug")
    line_number: str = Field(..., description="Line number where the bug is located")
    description: str = Field(..., description="Description of the bug")
    severity: str = Field(..., description="Severity of the bug (high, medium, low)")
    confidence: str = Field(..., description="Confidence level of the analysis (high, medium, low)")
    suggested_fix: str = Field(..., description="Suggested fix for the bug")
    code_snippet: str = Field(...,
                              description="Code snippet containing the bug, keep it short, not more than 5-10 lines.")


class BugAnalysisReport(BaseModel):
    """Model for the complete bug analysis report."""
    commit_id: str = Field(..., description="ID of the analyzed commit")
    timestamp: str = Field(..., description="Timestamp of the analysis")
    affected_files: List[str] = Field(..., description="List of files affected by the commit")
    bugs: List[BugAnalysis] = Field(default_factory=list, description="List of bugs found in the code")
    summary: Optional[str] = Field(None, description="Summary of the bug analysis")

    def to_xml(self) -> ET.Element:
        """Convert the bug analysis report to an XML element.

        Returns:
            An XML element representing the bug analysis report.
        """
        # Create the root element
        root = ET.Element("bug_analysis_report")

        # Add commit_id
        commit_id_elem = ET.SubElement(root, "commit_id")
        commit_id_elem.text = self.commit_id

        # Add timestamp
        timestamp_elem = ET.SubElement(root, "timestamp")
        timestamp_elem.text = self.timestamp

        # Add affected_files
        affected_files_elem = ET.SubElement(root, "affected_files")
        for file_path in self.affected_files:
            file_elem = ET.SubElement(affected_files_elem, "file")
            file_elem.text = file_path

        # Add bugs
        bugs_elem = ET.SubElement(root, "bugs")
        for bug in self.bugs:
            bug_elem = ET.SubElement(bugs_elem, "bug")

            file_path_elem = ET.SubElement(bug_elem, "file_path")
            file_path_elem.text = bug.file_path

            line_number_elem = ET.SubElement(bug_elem, "line_number")
            line_number_elem.text = str(bug.line_number)

            description_elem = ET.SubElement(bug_elem, "description")
            description_elem.text = bug.description

            severity_elem = ET.SubElement(bug_elem, "severity")
            severity_elem.text = bug.severity

            confidence_elem = ET.SubElement(bug_elem, "confidence")
            confidence_elem.text = bug.confidence

            suggested_fix_elem = ET.SubElement(bug_elem, "suggested_fix")
            suggested_fix_elem.text = bug.suggested_fix

            code_snippet_elem = ET.SubElement(bug_elem, "code_snippet")
            code_snippet_elem.text = bug.code_snippet

        # Add summary if it exists
        if self.summary is not None:
            summary_elem = ET.SubElement(root, "summary")
            summary_elem.text = self.summary

        return root


class BugAnalyzerProcessor(CodeProcessor):
    """Processor for analyzing bugs in code changes using OpenRouter."""

    def get_default_message(self) -> str:
        """Get the default message to pass to OpenRouter.

        Returns:
            Default message for OpenRouter.
        """
        return (
            "Analyze this code diff and the full source of affected files to identify potential bugs. "
            "Focus on bugs introduced by the changes in the diff. "
            "For each issue found, provide: "
            "1) a brief description, "
            "2) the line number(s), "
            "3) severity (high/medium/low), "
            "4) confidence level (high/medium/low), "
            "5) a suggested fix, and "
            "6) the relevant code snippet. "
            "DON'T mention bugs where no actual fix is need."
        )

    def get_description(self) -> str:
        """Get the description for the argument parser.

        Returns:
            Description string.
        """
        return "Analyze bugs in code changes using OpenRouter and output results as XML"

    def add_arguments(self, parser: argparse.ArgumentParser) -> None:
        """Add processor-specific arguments to the parser.

        Args:
            parser: The argument parser to add arguments to.
        """
        super().add_arguments(parser)
        parser.add_argument(
            "--commit",
            type=str,
            default="HEAD",
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
            "--output",
            type=str,
            default="bug_analysis_report.xml",
            help="Output file path for the bug analysis report (default: bug_analysis_report.xml)"
        )

    def change_working_directory(self, directory: str = "/src") -> bool:
        """Change the working directory to the specified directory (default: /src)."""
        try:
            logger.info(f"Changing working directory to: {directory}")
            os.chdir(directory)
            return True
        except Exception as e:
            logger.error(f"Error changing working directory to {directory}: {e}")
            return False

    def is_git_repository(self) -> bool:
        """Check if the current directory is a git repository.

        Returns:
            True if the current directory is a git repository, False otherwise.
        """
        try:
            result = subprocess.run(
                ["git", "rev-parse", "--is-inside-work-tree"],
                check=True,
                text=True,
                capture_output=True
            )
            return result.stdout.strip() == "true"
        except subprocess.CalledProcessError:
            return False
        except Exception as e:
            logger.warning(f"Error checking if directory is a git repository: {e}")
            return False

    def get_commit_diff(self, commit_id: Optional[str] = None, working_tree: bool = False, branch_diff: Optional[str] = None, remote_diff: bool = False) -> str:
        """Get the diff of a commit, working tree changes, branch diff, or remote diff.

        Args:
            commit_id: The ID of the commit to get the diff for (used if working_tree, branch_diff, and remote_diff are False).
            working_tree: If True, get the diff between working tree and HEAD.
            branch_diff: If provided, get the diff between current branch and specified branch.
            remote_diff: If True, get the diff between local branch and its remote counterpart.

        Returns:
            The diff of the commit, working tree changes, branch diff, or remote diff.
        """
        # Check if the current directory is a git repository
        if not self.is_git_repository():
            logger.error("Not a git repository. Cannot get diff.")
            return ""

        try:
            if remote_diff:
                # Get the current branch name
                current_branch_cmd = ["git", "rev-parse", "--abbrev-ref", "HEAD"]
                current_branch_result = subprocess.run(
                    current_branch_cmd,
                    check=True,
                    text=True,
                    capture_output=True
                )
                current_branch = current_branch_result.stdout.strip()

                # Get the remote tracking branch for the current branch
                remote_branch_cmd = ["git", "rev-parse", "--abbrev-ref", f"{current_branch}@{{upstream}}"]
                try:
                    remote_branch_result = subprocess.run(
                        remote_branch_cmd,
                        check=True,
                        text=True,
                        capture_output=True
                    )
                    remote_branch = remote_branch_result.stdout.strip()
                except subprocess.CalledProcessError:
                    logger.error(f"No upstream branch found for {current_branch}. Please set an upstream branch with 'git push -u origin {current_branch}'.")
                    return ""

                # Get diff between local branch and remote branch
                git_cmd = ["git", "diff", f"{remote_branch}...{current_branch}"]
                logger.debug(f"Running git diff for remote comparison: {' '.join(git_cmd)}")
                result = subprocess.run(
                    git_cmd,
                    check=True,
                    text=True,
                    capture_output=True
                )
                logger.debug(f"git diff output (remote diff {remote_branch}...{current_branch}):\n{result.stdout}")
            elif branch_diff:
                # Get the current branch name
                current_branch_cmd = ["git", "rev-parse", "--abbrev-ref", "HEAD"]
                current_branch_result = subprocess.run(
                    current_branch_cmd,
                    check=True,
                    text=True,
                    capture_output=True
                )
                current_branch = current_branch_result.stdout.strip()

                # Get diff between current branch and specified branch
                git_cmd = ["git", "diff", f"{branch_diff}...{current_branch}"]
                logger.debug(f"Running git diff for branch comparison: {' '.join(git_cmd)}")
                result = subprocess.run(
                    git_cmd,
                    check=True,
                    text=True,
                    capture_output=True
                )
                logger.debug(f"git diff output (branch diff {branch_diff}...{current_branch}):\n{result.stdout}")
            elif working_tree:
                git_cmd = ["git", "diff", "HEAD"]
                logger.debug(f"Running git diff for working tree: {' '.join(git_cmd)}")
                result = subprocess.run(
                    git_cmd,
                    check=True,
                    text=True,
                    capture_output=True
                )
                logger.debug(f"git diff output (working tree):\n{result.stdout}")
            else:
                if not commit_id:
                    raise ValueError("commit_id must be provided when working_tree and branch_diff are False")
                git_cmd = ["git", "show", commit_id]
                logger.debug(f"Running git show for commit: {' '.join(git_cmd)}")
                result = subprocess.run(
                    git_cmd,
                    check=True,
                    text=True,
                    capture_output=True
                )
                logger.debug(f"git show output (commit {commit_id}):\n{result.stdout}")
            return result.stdout
        except subprocess.CalledProcessError as e:
            logger.error(f"Error getting diff: {e}")
            logger.debug(f"git command failed: {e.cmd}\nstdout: {e.stdout}\nstderr: {e.stderr}")
            return ""

    def count_lines_in_file(self, file_path: str) -> int:
        """Count the number of lines in a file.

        Args:
            file_path: Path to the file.

        Returns:
            Number of lines in the file.
        """
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                return sum(1 for _ in f)
        except Exception as e:
            logger.warning(f"Error counting lines in file {file_path}: {e}")
            return 0

    def get_affected_files(self, commit_id: Optional[str] = None, working_tree: bool = False, branch_diff: Optional[str] = None, remote_diff: bool = False) -> List[str]:
        """Get the list of files affected by a commit, working tree changes, branch diff, or remote diff.

        Args:
            commit_id: The ID of the commit to get affected files for (used if working_tree, branch_diff, and remote_diff are False).
            working_tree: If True, get files changed in the working tree compared to HEAD.
            branch_diff: If provided, get files changed between current branch and specified branch.
            remote_diff: If True, get files changed between local branch and its remote counterpart.

        Returns:
            List of affected file paths.
        """
        # Check if the current directory is a git repository
        if not self.is_git_repository():
            logger.error("Not a git repository. Cannot get affected files.")
            return []

        try:
            if remote_diff:
                # Get the current branch name
                current_branch_cmd = ["git", "rev-parse", "--abbrev-ref", "HEAD"]
                current_branch_result = subprocess.run(
                    current_branch_cmd,
                    check=True,
                    text=True,
                    capture_output=True
                )
                current_branch = current_branch_result.stdout.strip()

                # Get the remote tracking branch for the current branch
                remote_branch_cmd = ["git", "rev-parse", "--abbrev-ref", f"{current_branch}@{{upstream}}"]
                try:
                    remote_branch_result = subprocess.run(
                        remote_branch_cmd,
                        check=True,
                        text=True,
                        capture_output=True
                    )
                    remote_branch = remote_branch_result.stdout.strip()
                except subprocess.CalledProcessError:
                    logger.error(f"No upstream branch found for {current_branch}. Please set an upstream branch with 'git push -u origin {current_branch}'.")
                    return []

                # Get files changed between local branch and remote branch
                result = subprocess.run(
                    ["git", "diff", "--name-only", f"{remote_branch}...{current_branch}"],
                    check=True,
                    text=True,
                    capture_output=True
                )
            elif branch_diff:
                # Get the current branch name
                current_branch_cmd = ["git", "rev-parse", "--abbrev-ref", "HEAD"]
                current_branch_result = subprocess.run(
                    current_branch_cmd,
                    check=True,
                    text=True,
                    capture_output=True
                )
                current_branch = current_branch_result.stdout.strip()

                # Get files changed between current branch and specified branch
                result = subprocess.run(
                    ["git", "diff", "--name-only", f"{branch_diff}...{current_branch}"],
                    check=True,
                    text=True,
                    capture_output=True
                )
            elif working_tree:
                # Get files changed in the working tree compared to HEAD
                result = subprocess.run(
                    ["git", "diff", "--name-only", "HEAD"],
                    check=True,
                    text=True,
                    capture_output=True
                )
            else:
                if not commit_id:
                    raise ValueError("commit_id must be provided when working_tree and branch_diff are False")
                # Get files affected by a specific commit
                result = subprocess.run(
                    ["git", "diff-tree", "--no-commit-id", "--name-only", "-r", commit_id],
                    check=True,
                    text=True,
                    capture_output=True
                )

            # Get all affected files
            all_files = [file.strip() for file in result.stdout.splitlines() if file.strip()]

            # Filter out files with more than 1000 lines
            filtered_files = []
            for file_path in all_files:
                if not file_path:
                    continue

                try:
                    line_count = self.count_lines_in_file(file_path)
                    if line_count <= 1000:
                        filtered_files.append(file_path)
                    else:
                        logger.info(f"Skipping file {file_path} with {line_count} lines (over 1000 lines limit)")
                except Exception as e:
                    logger.warning(f"Error processing file {file_path}: {e}")

            return filtered_files
        except subprocess.CalledProcessError as e:
            logger.error(f"Error getting affected files: {e}")
            return []

    def get_file_content(self, file_path: str) -> str:
        """Get the content of a file.

        Args:
            file_path: Path to the file.

        Returns:
            Content of the file.
        """
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                return f.read()
        except Exception as e:
            logger.warning(f"Error reading file {file_path}: {e}")
            return ""

    async def process_files(self, args: argparse.Namespace) -> Dict[str, Any]:
        """Process files and generate a bug analysis report.

        Args:
            args: Command line arguments.

        Returns:
            Dictionary containing the bug analysis report.
        """
        commit_id = args.commit
        output_file = args.output
        working_tree = args.working_tree
        branch_diff = getattr(args, 'branch_diff', None)
        remote_diff = getattr(args, 'remote_diff', False)
        directory = getattr(args, 'directory', '/src') or '/src'

        # Set logger to debug level if --debug is passed
        if getattr(args, 'debug', False):
            force_debug_logging(logger)

        # Change to the specified directory
        if not self.change_working_directory(directory):
            logger.error(f"Failed to change to directory: {directory}")
            # Create timestamp for the report
            timestamp = datetime.now().isoformat()
            # Write minimal XML report for directory change failure
            with open(output_file, 'w', encoding='utf-8') as f:
                f.write(f'''<?xml version="1.0" encoding="UTF-8"?>
<bug_analysis_report>
  <commit_id>{commit_id}</commit_id>
  <timestamp>{timestamp}</timestamp>
  <affected_files></affected_files>
  <bugs></bugs>
  <summary>Failed to change to directory: {directory}</summary>
</bug_analysis_report>
''')
            logger.info(f"Empty bug analysis report created at {output_file}")
            return {}

        # Check if the current directory is a git repository
        if not self.is_git_repository():
            logger.error("Not a git repository. Cannot analyze code.")
            # Create timestamp for the report
            timestamp = datetime.now().isoformat()
            # Write minimal XML report for non-git directory
            with open(output_file, 'w', encoding='utf-8') as f:
                f.write(f'''<?xml version="1.0" encoding="UTF-8"?>
<bug_analysis_report>
  <commit_id>{commit_id}</commit_id>
  <timestamp>{timestamp}</timestamp>
  <affected_files></affected_files>
  <bugs></bugs>
  <summary>The specified directory is not a git repository. Cannot analyze code.</summary>
</bug_analysis_report>
''')
            logger.info(f"Empty bug analysis report created at {output_file}")
            return {}

        # Determine the mode of operation
        if remote_diff:
            mode_desc = "diff between local branch and its remote counterpart"
        elif branch_diff:
            mode_desc = f"diff between current branch and {branch_diff}"
        elif working_tree:
            mode_desc = "working tree changes"
        else:
            mode_desc = f"commit {commit_id}"

        # Create timestamp for the report
        timestamp = datetime.now().isoformat()

        # Get the diff
        logger.info(f"Getting diff for {mode_desc}")
        logger.debug(f"About to gather diff for {mode_desc} (commit_id={commit_id}, working_tree={working_tree}, branch_diff={branch_diff}, remote_diff={remote_diff})")
        commit_diff = self.get_commit_diff(commit_id, working_tree, branch_diff, remote_diff)
        logger.debug(f"Diff gathered for {mode_desc}:\n{commit_diff}")
        if not commit_diff:
            logger.error(f"Failed to get diff for {mode_desc}")
            # Write minimal XML report for empty diff
            with open(output_file, 'w', encoding='utf-8') as f:
                f.write(f'''<?xml version="1.0" encoding="UTF-8"?>
<bug_analysis_report>
  <commit_id>{commit_id}</commit_id>
  <timestamp>{timestamp}</timestamp>
  <affected_files></affected_files>
  <bugs></bugs>
  <summary>No diff found for {mode_desc}.</summary>
</bug_analysis_report>
''')
            logger.info(f"Empty bug analysis report created at {output_file}")
            return {}

        # Get the list of affected files
        logger.info(f"Getting affected files for {mode_desc}")
        affected_files = self.get_affected_files(commit_id, working_tree, branch_diff, remote_diff)
        if not affected_files:
            logger.warning(f"No affected files found for {mode_desc}")
            # Write minimal XML report with no bugs
            with open(output_file, 'w', encoding='utf-8') as f:
                f.write(f'''<?xml version="1.0" encoding="UTF-8"?>
<bug_analysis_report>
  <commit_id>{commit_id}</commit_id>
  <timestamp>{timestamp}</timestamp>
  <affected_files></affected_files>
  <bugs></bugs>
  <summary>No affected files found.</summary>
</bug_analysis_report>
''')
            logger.info(f"Empty bug analysis report created at {output_file}")
            return {}

        # Get the content of each affected file
        file_contents = {}
        for file_path in affected_files:
            logger.info(f"Reading content of file {file_path}")
            content = self.get_file_content(file_path)
            if content:
                file_contents[file_path] = content

        # Timestamp already created at the beginning of the method

        input_data = {
            "commit_id": commit_id,
            "commit_diff": commit_diff,
            "affected_files": affected_files,
            "file_contents": file_contents,
            "timestamp": timestamp
        }
        # logger.debug(f"input_data: {input_data}")
        bug_analysis_report: BugAnalysisReport = await schema_cat.prompt_with_schema(json.dumps(input_data, indent=2),
                                                                                     BugAnalysisReport,
                                                                                     "openai/gpt-4.1-mini",
                                                                                     schema_cat.Provider.OPENROUTER,
                                                                                     sys_prompt=self.get_default_message())

        # Write the parsed XML to file
        with open(output_file, 'w', encoding='utf-8') as f:
            f.write('<?xml version="1.0" encoding="UTF-8"?>\n')
            # Convert the bug analysis report to XML and write it to the file
            root = bug_analysis_report.to_xml()
            xml_string = ET.tostring(root, encoding='unicode')
            f.write(xml_string)

        logger.info(f"Bug analysis report created at {output_file}")

        # For compatibility with existing code, also return as dict
        return bug_analysis_report.model_dump()

    def run(self) -> None:
        """Run the bug analyzer processor."""
        args = self.parse_args()
        # Run the asynchronous process_files method in an event loop
        asyncio.run(self.process_files(args))


def main() -> None:
    """Main entry point for the bug analyzer processor."""
    processor = BugAnalyzerProcessor()
    processor.run()


if __name__ == "__main__":
    main()
