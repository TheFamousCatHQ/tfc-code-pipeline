#!/usr/bin/env python3
"""
Script to analyze bugs in code changes using OpenRouter.

This script can operate in two modes:
1. Commit mode: Takes the diff of a commit, plus the full source of all affected files.
2. Working tree mode: Takes the diff between the working tree and HEAD, plus the full source of all affected files.

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

import httpx
from pydantic import BaseModel, Field

from ai import xml_from_string
from code_processor import CodeProcessor
from logging_utils import get_logger

# Set up logging
logger = get_logger("tfc-code-pipeline.bug_analyzer")


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
            "6) the relevant code snippet. "
            "Return the results in XML format using the following structure:\n"
            "<bug_analysis_report>\n"
            "  <commit_id>ID of the analyzed commit</commit_id>\n"
            "  <timestamp>Timestamp of the analysis</timestamp>\n"
            "  <affected_files>\n"
            "    <file>path/to/file1.py</file>\n"
            "    <file>path/to/file2.py</file>\n"
            "  </affected_files>\n"
            "  <bugs>\n"
            "    <bug>\n"
            "      <file_path>path/to/file.py</file_path>\n"
            "      <line_number>42</line_number>\n"
            "      <bug_description>Description of the bug</bug_description>\n"
            "      <severity>high|medium|low</severity>\n"
            "      <confidence>high|medium|low</confidence>\n"
            "      <suggested_fix><![CDATA[code to fix the bug]]></suggested_fix>\n"
            "      <code_snippet><![CDATA[code containing the bug]]></code_snippet>\n"
            "    </bug>\n"
            "  </bugs>\n"
            "  <summary>Overall summary of the bug analysis</summary>\n"
            "</bug_analysis_report>\n"
            "Only return the XML, nothing else."
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
            "--output",
            type=str,
            default="bug_analysis_report.xml",
            help="Output file path for the bug analysis report (default: bug_analysis_report.xml)"
        )

    def get_commit_diff(self, commit_id: Optional[str] = None, working_tree: bool = False) -> str:
        """Get the diff of a commit or working tree changes.

        Args:
            commit_id: The ID of the commit to get the diff for (used if working_tree is False).
            working_tree: If True, get the diff between working tree and HEAD.

        Returns:
            The diff of the commit or working tree changes.
        """
        try:
            if working_tree:
                # Get diff between working tree and HEAD
                result = subprocess.run(
                    ["git", "diff", "HEAD"],
                    check=True,
                    text=True,
                    capture_output=True
                )
            else:
                if not commit_id:
                    raise ValueError("commit_id must be provided when working_tree is False")
                # Get diff of a specific commit
                result = subprocess.run(
                    ["git", "show", commit_id],
                    check=True,
                    text=True,
                    capture_output=True
                )
            return result.stdout
        except subprocess.CalledProcessError as e:
            logger.error(f"Error getting diff: {e}")
            return ""

    def get_affected_files(self, commit_id: Optional[str] = None, working_tree: bool = False) -> List[str]:
        """Get the list of files affected by a commit or working tree changes.

        Args:
            commit_id: The ID of the commit to get affected files for (used if working_tree is False).
            working_tree: If True, get files changed in the working tree compared to HEAD.

        Returns:
            List of affected file paths.
        """
        try:
            if working_tree:
                # Get files changed in the working tree compared to HEAD
                result = subprocess.run(
                    ["git", "diff", "--name-only", "HEAD"],
                    check=True,
                    text=True,
                    capture_output=True
                )
            else:
                if not commit_id:
                    raise ValueError("commit_id must be provided when working_tree is False")
                # Get files affected by a specific commit
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
            with open(file_path, 'r', encoding='utf-8') as f:
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
        working_tree = args.working_tree

        # Determine the mode of operation
        mode_desc = "working tree changes" if working_tree else f"commit {commit_id}"

        # Get the diff
        logger.info(f"Getting diff for {mode_desc}")
        commit_diff = self.get_commit_diff(commit_id, working_tree)
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
        affected_files = self.get_affected_files(commit_id, working_tree)
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

        # Prepare the input for OpenRouter
        timestamp = datetime.now().isoformat()

        input_data = {
            "commit_id": commit_id,
            "commit_diff": commit_diff,
            "affected_files": affected_files,
            "file_contents": file_contents,
            "timestamp": timestamp
        }
        # logger.debug(f"input_data: {input_data}")

        # Set up OpenRouter API call
        logger.info("Setting up direct OpenRouter API call for bug analysis")
        api_key = os.getenv("OPENROUTER_API_KEY")
        base_url = os.getenv("OPENROUTER_BASE_URL", "https://openrouter.ai/api/v1")
        model = os.getenv("DEFAULT_MODEL", "openai/gpt-4.1-mini")

        headers = {
            "Authorization": f"Bearer {api_key}",
            "HTTP-Referer": os.getenv("OPENROUTER_HTTP_REFERER", "https://www.thefamouscat.com"),
            "X-Title": os.getenv("OPENROUTER_X_TITLE", "CodePipeline"),
            "Content-Type": "application/json"
        }

        # Prepare the data payload
        data = {
            "model": model,
            "messages": [
                {"role": "system", "content": self.get_default_message()},
                {"role": "user", "content": json.dumps(input_data, indent=2)}
            ],
            "max_tokens": int(os.getenv("DEFAULT_MAX_TOKENS", "16384")),
            "temperature": float(os.getenv("DEFAULT_TEMPERATURE", "0"))
        }

        # Generate the bug analysis report
        try:
            logger.info(f"Calling OpenRouter API directly with model {model}")
            async with httpx.AsyncClient() as client:
                response = await client.post(
                    f"{base_url}/chat/completions",
                    headers=headers,
                    json=data,
                    timeout=60
                )
                response.raise_for_status()
                content = response.json()["choices"][0]["message"]["content"].strip()

            logger.info("Successfully received response from OpenRouter")
            logger.debug(f"Raw response content: {content}")

            # Parse the response content as XML
            # Try to extract XML from the response
            try:
                root = xml_from_string(content)
                logger.info("Successfully parsed response as XML")
            except Exception as e:
                logger.error(f"Failed to parse response as XML: {e}")
                logger.debug(f"Response content: {content}")
                return {}

            # Extract data from XML to create a BugAnalysisReport object
            commit_id = root.findtext("commit_id", "")
            timestamp = root.findtext("timestamp", "")
            summary = root.findtext("summary", "")

            # Extract affected files
            affected_files = []
            affected_files_elem = root.find("affected_files")
            if affected_files_elem is not None:
                for file_elem in affected_files_elem.findall("file"):
                    if file_elem.text:
                        affected_files.append(file_elem.text)

            # Extract bugs
            bugs = []
            bugs_elem = root.find("bugs")
            if bugs_elem is not None:
                for bug_elem in bugs_elem.findall("bug"):
                    file_path = bug_elem.findtext("file_path", "")
                    line_number_text = bug_elem.findtext("line_number", "0")
                    try:
                        line_number = int(line_number_text)
                    except ValueError:
                        line_number = 0
                    bug_description = bug_elem.findtext("bug_description", "")
                    severity = bug_elem.findtext("severity", "")
                    confidence = bug_elem.findtext("confidence", "")
                    suggested_fix = bug_elem.findtext("suggested_fix", "")
                    code_snippet = bug_elem.findtext("code_snippet", "")

                    bug = BugAnalysis(
                        file_path=file_path,
                        line_number=line_number,
                        bug_description=bug_description,
                        severity=severity,
                        confidence=confidence,
                        suggested_fix=suggested_fix,
                        code_snippet=code_snippet
                    )
                    bugs.append(bug)

            # Create a BugAnalysisReport object
            bug_analysis_report = BugAnalysisReport(
                commit_id=commit_id,
                timestamp=timestamp,
                affected_files=affected_files,
                bugs=bugs,
                summary=summary
            )
            logger.info("Successfully created BugAnalysisReport from XML")

            # Write the parsed XML to file
            with open(output_file, 'w', encoding='utf-8') as f:
                f.write('<?xml version="1.0" encoding="UTF-8"?>\n')
                # Convert the parsed XML structure to a string and write it to the file
                xml_string = ET.tostring(root, encoding='unicode')
                f.write(xml_string)

            logger.info(f"Bug analysis report created at {output_file}")

            # For compatibility with existing code, also return as dict
            return bug_analysis_report.model_dump()

        except Exception as e:
            logger.error(f"Failed to process XML response: {e}")
            logger.debug(f"Response content: {content}")
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
