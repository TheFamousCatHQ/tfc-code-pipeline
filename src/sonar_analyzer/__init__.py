"""
Sonar Analyzer module for analyzing Sonar scanner reports and generating improvement suggestions.

This module provides a CLI tool that takes a Sonar scanner report, analyzes the issues for each
component/file, and creates suggestions for improvements including prompts suitable for AI Coding Agents.
"""

import argparse
import json
import os
from collections import defaultdict
from enum import Enum
from pathlib import Path
from typing import Dict, List, Optional, Set, Tuple, Union

from code_processor import CodeProcessor
from logging_utils import get_logger

# Set up logging
logger = get_logger()


class SeverityLevel(Enum):
    """Enum for Sonar issue severity levels."""
    LOW = 1
    INFO = 2
    MEDIUM = 3
    HIGH = 4
    BLOCKER = 5

    @classmethod
    def from_string(cls, severity: str) -> 'SeverityLevel':
        """Convert a string severity to a SeverityLevel enum."""
        severity_map = {
            "LOW": cls.LOW,
            "INFO": cls.INFO,
            "MEDIUM": cls.MEDIUM,
            "HIGH": cls.HIGH,
            "BLOCKER": cls.BLOCKER,
            # Map legacy severity levels for compatibility
            "MINOR": cls.LOW,
            "MAJOR": cls.HIGH,
            "CRITICAL": cls.HIGH
        }
        return severity_map.get(severity.upper(), cls.INFO)

    @classmethod
    def to_string(cls, level: 'SeverityLevel') -> str:
        """Convert a SeverityLevel enum to a string."""
        severity_map = {
            cls.LOW: "LOW",
            cls.INFO: "INFO",
            cls.MEDIUM: "MEDIUM",
            cls.HIGH: "HIGH",
            cls.BLOCKER: "BLOCKER"
        }
        return severity_map.get(level, "INFO")


class SonarAnalyzerProcessor(CodeProcessor):
    """Processor for analyzing Sonar scanner reports and generating improvement suggestions."""

    def get_default_message(self) -> str:
        """Return the default message for the processor."""
        return "Analyze Sonar scanner report and generate improvement suggestions"

    def get_description(self) -> str:
        """Return a description of the processor."""
        return (
            "Analyzes a Sonar scanner report and generates improvement suggestions "
            "for each component/file, including prompts suitable for AI Coding Agents."
        )

    def add_arguments(self, parser: argparse.ArgumentParser) -> None:
        """Add command-line arguments to the parser."""
        super().add_arguments(parser)

        parser.add_argument(
            "--report-file",
            type=str,
            required=True,
            help="Path to the Sonar scanner report JSON file",
        )

        parser.add_argument(
            "--min-severity",
            type=str,
            default="MEDIUM",
            choices=["LOW", "INFO", "MEDIUM", "HIGH", "BLOCKER"],
            help="Minimum severity level to include in the analysis (default: MEDIUM)",
        )

        parser.add_argument(
            "--output-file",
            type=str,
            help="Path to the output file for the analysis results (default: stdout)",
        )

    def process_files(self, args: argparse.Namespace) -> List[str]:
        """Process the Sonar scanner report and generate improvement suggestions.

        Returns:
            List containing the report file path to indicate successful processing.
        """
        report_file = args.report_file
        min_severity = args.min_severity
        output_file = args.output_file

        logger.info(f"Analyzing Sonar scanner report: {report_file}")
        logger.info(f"Minimum severity level: {min_severity}")

        # Load the Sonar scanner report
        try:
            with open(report_file, 'r') as f:
                report_data = json.load(f)
        except Exception as e:
            logger.error(f"Failed to load Sonar scanner report: {e}")
            return []

        # Convert min_severity to SeverityLevel enum
        min_severity_level = SeverityLevel.from_string(min_severity)

        # Analyze the report and generate suggestions
        suggestions = self._analyze_report(report_data, min_severity_level)

        # Output the suggestions
        if output_file:
            try:
                with open(output_file, 'w') as f:
                    json.dump(suggestions, f, indent=2)
                logger.info(f"Analysis results written to: {output_file}")
            except Exception as e:
                logger.error(f"Failed to write analysis results: {e}")
                # Fall back to stdout
                self._print_suggestions(suggestions)
        else:
            # Print to stdout
            self._print_suggestions(suggestions)

        # Return the report file to indicate successful processing
        return [report_file]

    def _analyze_report(self, report_data: Dict, min_severity_level: SeverityLevel) -> Dict:
        """
        Analyze the Sonar scanner report and generate improvement suggestions.

        Args:
            report_data: The Sonar scanner report data
            min_severity_level: The minimum severity level to include

        Returns:
            A dictionary of suggestions for each component/file
        """
        suggestions = {}

        # Process issues
        if 'issues' in report_data and 'issues' in report_data['issues']:
            # Group issues by component
            issues_by_component = defaultdict(list)
            for issue in report_data['issues']['issues']:
                severity = issue.get('severity', 'INFO')
                severity_level = SeverityLevel.from_string(severity)

                # Skip issues below the minimum severity level
                if severity_level.value < min_severity_level.value:
                    continue

                component = issue.get('component', '')
                issues_by_component[component].append(issue)

            # Generate suggestions for each component with issues
            for component, issues in issues_by_component.items():
                if not issues:
                    continue

                # Generate a suggestion for the component based on issues
                suggestion = self._generate_suggestion(component, issues)
                if suggestion:
                    suggestions[component] = suggestion
        else:
            logger.warning("No issues found in the Sonar scanner report")

        # Process file measures for complexity
        if 'file_measures' in report_data and 'components' in report_data['file_measures']:
            # Analyze file complexity
            complex_files = self._analyze_file_complexity(report_data['file_measures']['components'])

            # Generate suggestions for complex files
            for component, complexity_data in complex_files.items():
                if component in suggestions:
                    # Component already has issues, add complexity information
                    suggestions[component]["complexity_data"] = complexity_data
                    suggestions[component]["prompt"] = self._combine_prompts(
                        suggestions[component]["prompt"],
                        self._generate_complexity_prompt(component, complexity_data)
                    )
                else:
                    # Component only has complexity issues
                    suggestions[component] = self._generate_complexity_suggestion(component, complexity_data)
        else:
            logger.warning("No file measures found in the Sonar scanner report")

        return suggestions

    def _generate_suggestion(self, component: str, issues: List[Dict]) -> Dict:
        """
        Generate an improvement suggestion for a component based on its issues.

        Args:
            component: The component name
            issues: The list of issues for the component

        Returns:
            A dictionary containing the suggestion details
        """
        if not issues:
            return {
                "component": component,
                "suggestion": "NONE",
                "prompt": ""
            }

        # Group issues by rule
        issues_by_rule = defaultdict(list)
        for issue in issues:
            rule = issue.get('rule', '')
            issues_by_rule[rule].append(issue)

        # Generate a summary of the issues
        summary = []
        for rule, rule_issues in issues_by_rule.items():
            rule_summary = f"Rule: {rule} ({len(rule_issues)} issues)"
            summary.append(rule_summary)

        # Generate a prompt for an AI Coding Agent
        prompt = self._generate_ai_prompt(component, issues)

        return {
            "component": component,
            "issues_count": len(issues),
            "summary": summary,
            "suggestion": "Fix the issues identified by Sonar scanner",
            "prompt": prompt
        }

    def _generate_ai_prompt(self, component: str, issues: List[Dict]) -> str:
        """
        Generate a prompt for an AI Coding Agent to fix the issues.

        Args:
            component: The component name
            issues: The list of issues for the component

        Returns:
            A prompt string
        """
        # Extract the file path from the component
        file_path = component.split(':')[-1] if ':' in component else component

        # Generate a detailed description of the issues
        issues_description = []
        for i, issue in enumerate(issues, 1):
            rule = issue.get('rule', '')
            severity = issue.get('severity', 'INFO')
            line = issue.get('line', 'N/A')
            message = issue.get('message', 'No description available')

            issue_desc = (
                f"Issue {i}:\n"
                f"  Rule: {rule}\n"
                f"  Severity: {severity}\n"
                f"  Line: {line}\n"
                f"  Message: {message}"
            )
            issues_description.append(issue_desc)

        # Create the prompt
        prompt = (
            f"Please fix the following Sonar scanner issues in the file '{file_path}':\n\n"
            f"{chr(10).join(issues_description)}\n\n"
            f"Please provide the necessary code changes to fix these issues, "
            f"following best practices and maintaining the existing functionality."
        )

        return prompt

    def _analyze_file_complexity(self, components: List[Dict]) -> Dict[str, Dict]:
        """
        Analyze file complexity and identify overly complex files.

        Args:
            components: List of components from file_measures

        Returns:
            Dictionary of complex files with their complexity metrics
        """
        # Define thresholds for complexity
        COMPLEXITY_THRESHOLD = 30  # Cyclomatic complexity
        COGNITIVE_COMPLEXITY_THRESHOLD = 25  # Cognitive complexity
        NCLOC_THRESHOLD = 500  # Number of lines of code

        complex_files = {}

        for component in components:
            key = component.get('key', '')
            measures = component.get('measures', [])

            # Extract complexity metrics
            complexity = None
            cognitive_complexity = None
            ncloc = None
            functions = None

            for measure in measures:
                metric = measure.get('metric', '')
                value = measure.get('value', '0')

                if metric == 'complexity':
                    complexity = int(value) if value.isdigit() else 0
                elif metric == 'cognitive_complexity':
                    cognitive_complexity = int(value) if value.isdigit() else 0
                elif metric == 'ncloc':
                    ncloc = int(value) if value.isdigit() else 0
                elif metric == 'functions':
                    functions = int(value) if value.isdigit() else 0

            # Check if the file is complex
            is_complex = False
            complexity_reasons = []

            if complexity and complexity > COMPLEXITY_THRESHOLD:
                is_complex = True
                complexity_reasons.append(f"High cyclomatic complexity: {complexity} (threshold: {COMPLEXITY_THRESHOLD})")

            if cognitive_complexity and cognitive_complexity > COGNITIVE_COMPLEXITY_THRESHOLD:
                is_complex = True
                complexity_reasons.append(f"High cognitive complexity: {cognitive_complexity} (threshold: {COGNITIVE_COMPLEXITY_THRESHOLD})")

            if ncloc and ncloc > NCLOC_THRESHOLD:
                is_complex = True
                complexity_reasons.append(f"Large file size: {ncloc} lines of code (threshold: {NCLOC_THRESHOLD})")

            # Calculate complexity per function if possible
            complexity_per_function = None
            if complexity and functions and functions > 0:
                complexity_per_function = complexity / functions
                if complexity_per_function > 5:  # Threshold for complexity per function
                    is_complex = True
                    complexity_reasons.append(f"High average complexity per function: {complexity_per_function:.2f} (threshold: 5)")

            if is_complex:
                complex_files[key] = {
                    "complexity": complexity,
                    "cognitive_complexity": cognitive_complexity,
                    "ncloc": ncloc,
                    "functions": functions,
                    "complexity_per_function": complexity_per_function,
                    "reasons": complexity_reasons
                }

        return complex_files

    def _generate_complexity_suggestion(self, component: str, complexity_data: Dict) -> Dict:
        """
        Generate a suggestion for a complex file.

        Args:
            component: The component name
            complexity_data: Complexity metrics and reasons

        Returns:
            A dictionary containing the suggestion details
        """
        # Extract complexity reasons
        reasons = complexity_data.get('reasons', [])

        # Generate a summary
        summary = [f"Complexity issue: {reason}" for reason in reasons]

        # Generate a prompt
        prompt = self._generate_complexity_prompt(component, complexity_data)

        return {
            "component": component,
            "complexity_data": complexity_data,
            "summary": summary,
            "suggestion": "Refactor to reduce complexity",
            "prompt": prompt,
            "issues_count": 0  # No Sonar issues, only complexity
        }

    def _generate_complexity_prompt(self, component: str, complexity_data: Dict) -> str:
        """
        Generate a prompt for refactoring a complex file.

        Args:
            component: The component name
            complexity_data: Complexity metrics and reasons

        Returns:
            A prompt string
        """
        # Extract the file path from the component
        file_path = component.split(':')[-1] if ':' in component else component

        # Extract complexity metrics
        complexity = complexity_data.get('complexity', 'N/A')
        cognitive_complexity = complexity_data.get('cognitive_complexity', 'N/A')
        ncloc = complexity_data.get('ncloc', 'N/A')
        functions = complexity_data.get('functions', 'N/A')
        complexity_per_function = complexity_data.get('complexity_per_function', 'N/A')
        if complexity_per_function is not None:
            complexity_per_function = f"{complexity_per_function:.2f}"

        # Extract reasons
        reasons = complexity_data.get('reasons', [])
        reasons_text = "\n".join([f"- {reason}" for reason in reasons])

        # Create the prompt
        prompt = (
            f"Please refactor the file '{file_path}' to reduce its complexity. The file has the following complexity issues:\n\n"
            f"{reasons_text}\n\n"
            f"Complexity metrics:\n"
            f"- Cyclomatic complexity: {complexity}\n"
            f"- Cognitive complexity: {cognitive_complexity}\n"
            f"- Lines of code: {ncloc}\n"
            f"- Number of functions: {functions}\n"
            f"- Average complexity per function: {complexity_per_function}\n\n"
            f"Please suggest refactoring strategies to reduce the complexity while maintaining the existing functionality. "
            f"Consider techniques such as:\n"
            f"- Breaking down complex functions into smaller, more focused functions\n"
            f"- Extracting complex logic into separate classes or modules\n"
            f"- Simplifying conditional logic\n"
            f"- Removing duplication\n"
            f"- Improving naming and documentation"
        )

        return prompt

    def _combine_prompts(self, issues_prompt: str, complexity_prompt: str) -> str:
        """
        Combine issue and complexity prompts.

        Args:
            issues_prompt: The prompt for fixing issues
            complexity_prompt: The prompt for reducing complexity

        Returns:
            A combined prompt
        """
        return (
            f"{issues_prompt}\n\n"
            f"Additionally, this file has complexity issues that should be addressed:\n\n"
            f"{complexity_prompt}"
        )

    def _print_suggestions(self, suggestions: Dict) -> None:
        """
        Print the suggestions to stdout.

        Args:
            suggestions: The suggestions dictionary
        """
        if not suggestions:
            print("No suggestions generated.")
            return

        print(f"Generated {len(suggestions)} suggestions:")
        print()

        for component, suggestion in suggestions.items():
            print(f"Component: {component}")

            # Print issues information if available
            if 'issues_count' in suggestion:
                print(f"Issues Count: {suggestion['issues_count']}")

            # Print complexity information if available
            if 'complexity_data' in suggestion:
                complexity_data = suggestion['complexity_data']
                print("Complexity Metrics:")
                print(f"  - Cyclomatic complexity: {complexity_data.get('complexity', 'N/A')}")
                print(f"  - Cognitive complexity: {complexity_data.get('cognitive_complexity', 'N/A')}")
                print(f"  - Lines of code: {complexity_data.get('ncloc', 'N/A')}")
                print(f"  - Functions: {complexity_data.get('functions', 'N/A')}")
                if complexity_data.get('complexity_per_function') is not None:
                    print(f"  - Complexity per function: {complexity_data.get('complexity_per_function'):.2f}")

            # Print summary
            print("Summary:")
            for summary_item in suggestion['summary']:
                print(f"  - {summary_item}")

            print(f"Suggestion: {suggestion['suggestion']}")
            print("Prompt for AI Coding Agent:")
            print(f"{suggestion['prompt']}")
            print("-" * 80)
            print()


def main():
    """Entry point for the Sonar analyzer CLI tool."""
    processor = SonarAnalyzerProcessor()
    processor.run()


if __name__ == "__main__":
    main()
