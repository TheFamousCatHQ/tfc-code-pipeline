#!/usr/bin/env python3
"""
Script to analyze bugs in code changes using OpenRouter.

This script takes the diff of a commit, plus the full source of all affected files,
feeds that to OpenRouter, and asks for a bug analysis. The output is in a standardized
JSON format.
"""

import argparse
import asyncio
import json
import subprocess
from datetime import datetime
from typing import Dict, List, Any

from pydantic import BaseModel, Field

from ai import create_agent
from code_processor import CodeProcessor
from logging_utils import get_logger

# Set up logging
logger = get_logger()


class BugAnalysis(BaseModel):
    """Model for bug analysis results."""
    file_path: str = Field(..., description="Path to the file containing the bug")
    line_number: int = Field(..., description="Line number where the bug is located")
    bug_description: str = Field(..., description="Description of the bug")
    severity: str = Field(..., description="Severity of the bug (high, medium, low)")
    confidence: str = Field(..., description="Confidence level of the analysis (high, medium, low)")
    suggested_fix: str = Field(..., description="Suggested fix for the bug")
    code_snippet: str = Field(..., description="Code snippet containing the bug")


class BugAnalysisReport(BaseModel):
    """Model for the complete bug analysis report."""
    commit_id: str = Field(..., description="ID of the analyzed commit")
    timestamp: str = Field(..., description="Timestamp of the analysis")
    affected_files: List[str] = Field(..., description="List of files affected by the commit")
    bugs: List[BugAnalysis] = Field(default_factory=list, description="List of bugs found in the code")
    summary: str = Field(..., description="Summary of the bug analysis")


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
            "6) the relevant code snippet."
        )

    def get_description(self) -> str:
        """Get the description for the argument parser.

        Returns:
            Description string.
        """
        return "Analyze bugs in code changes using OpenRouter and output results as JSON"

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
            "--output",
            type=str,
            default="bug_analysis_report.json",
            help="Output file path for the bug analysis report (default: bug_analysis_report.json)"
        )

    def get_commit_diff(self, commit_id: str) -> str:
        """Get the diff of a commit.

        Args:
            commit_id: The ID of the commit to get the diff for.

        Returns:
            The diff of the commit.
        """
        try:
            result = subprocess.run(
                ["git", "show", commit_id],
                check=True,
                text=True,
                capture_output=True
            )
            return result.stdout
        except subprocess.CalledProcessError as e:
            logger.error(f"Error getting commit diff: {e}")
            return ""

    def get_affected_files(self, commit_id: str) -> List[str]:
        """Get the list of files affected by a commit.

        Args:
            commit_id: The ID of the commit to get affected files for.

        Returns:
            List of affected file paths.
        """
        try:
            result = subprocess.run(
                ["git", "diff-tree", "--no-commit-id", "--name-only", "-r", commit_id],
                check=True,
                text=True,
                capture_output=True
            )
            return [file.strip() for file in result.stdout.splitlines() if file.strip()]
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
            with open(file_path, 'r') as f:
                return f.read()
        except Exception as e:
            logger.error(f"Error reading file {file_path}: {e}")
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

        # Get the commit diff
        logger.info(f"Getting diff for commit {commit_id}")
        commit_diff = self.get_commit_diff(commit_id)
        if not commit_diff:
            logger.error(f"Failed to get diff for commit {commit_id}")
            return {}

        # Get the list of affected files
        logger.info(f"Getting affected files for commit {commit_id}")
        affected_files = self.get_affected_files(commit_id)
        if not affected_files:
            logger.warning(f"No affected files found for commit {commit_id}")
            return {}

        # Get the content of each affected file
        file_contents = {}
        for file_path in affected_files:
            logger.info(f"Reading content of file {file_path}")
            content = self.get_file_content(file_path)
            if content:
                file_contents[file_path] = content

        # Prepare the input for OpenRouter
        timestamp = datetime.now().isoformat()

        input_data = {
            "commit_id": commit_id,
            "commit_diff": commit_diff,
            "affected_files": affected_files,
            "file_contents": file_contents,
            "timestamp": timestamp
        }

        # Create an agent using the ai module
        logger.info("Creating OpenRouter agent for bug analysis")
        agent = create_agent(
            output_type=BugAnalysisReport,
            system_prompt=self.get_default_message(),
            retries=3,
            output_retries=3
        )

        # Generate the bug analysis report
        try:
            logger.info("Generating bug analysis report using OpenRouter")
            # Await the asynchronous run method
            bug_analysis_report = await agent.run(input_data)
            logger.info("Successfully generated bug analysis report")

            # Convert to dict and write to file
            report_dict = bug_analysis_report.model_dump()
            with open(output_file, 'w') as f:
                json.dump(report_dict, f, indent=2)

            logger.info(f"Bug analysis report created at {output_file}")
            return report_dict

        except Exception as e:
            logger.error(f"Error generating bug analysis report: {e}")
            logger.debug("Exception details:", exc_info=True)
            return {}

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
