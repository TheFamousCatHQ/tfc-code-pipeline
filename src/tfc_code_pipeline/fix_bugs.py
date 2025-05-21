"""
Processor to run bug_analyzer and then feed its XML output to aider to fix the bugs, or to use a pre-produced bug analysis report.
"""

import argparse
import subprocess
import xml.etree.ElementTree as ET
from pathlib import Path
from typing import List, Optional, Sequence

from code_processor import CodeProcessor
from logging_utils import get_logger

logger = get_logger("tfc-code-pipeline.fix_bugs")


class FixBugsProcessor(CodeProcessor):
    """Processor to run bug_analyzer and then feed its XML output to aider to fix the bugs, or to use a pre-produced bug analysis report."""

    def get_default_message(self) -> str:
        """Get the default message to pass to aider."""
        return (
            "Here is a bug analysis report in XML format. For each bug, please fix the code in the specified file and line. "
            "Apply the suggested fix if possible, or otherwise address the described issue. "
            "Do not make unrelated changes."
        )

    def get_description(self) -> str:
        return "Run bug_analyzer, then feed its XML output to aider to fix the bugs, or use a pre-produced bug analysis report."

    def extract_file_paths(self, xml_path: Path) -> List[str]:
        """Extract file paths from the bug analysis report XML.

        Args:
            xml_path: Path to the bug analysis report XML file.

        Returns:
            List of file paths mentioned in the report.
        """
        try:
            tree = ET.parse(xml_path)
            root = tree.getroot()

            file_paths = []

            # Extract files from affected_files element
            affected_files_elem = root.find("affected_files")
            if affected_files_elem is not None:
                for file_elem in affected_files_elem.findall("file"):
                    if file_elem.text and file_elem.text.strip():
                        file_paths.append(file_elem.text.strip())

            # Extract files from bugs element
            bugs_elem = root.find("bugs")
            if bugs_elem is not None:
                for bug_elem in bugs_elem.findall("bug"):
                    file_path_elem = bug_elem.find("file_path")
                    if file_path_elem is not None and file_path_elem.text and file_path_elem.text.strip():
                        file_path = file_path_elem.text.strip()
                        if file_path not in file_paths:
                            file_paths.append(file_path)

            return file_paths
        except Exception as e:
            logger.error(f"Error extracting file paths from XML: {e}")
            return []

    def add_arguments(self, parser: argparse.ArgumentParser) -> None:
        parser.add_argument(
            "--output",
            type=str,
            default="bug_analysis_report.xml",
            help="Output file path for the bug analysis report (default: bug_analysis_report.xml)"
        )
        parser.add_argument(
            "--debug",
            action="store_true",
            help="Run aider with --pretty and --stream flags for debugging"
        )
        parser.add_argument(
            "--working-tree",
            action="store_true",
            help="Analyze diff between working tree and HEAD (default: False)"
        )
        parser.add_argument(
            "--commit",
            type=str,
            help="Commit ID to analyze (optional, overrides working tree if provided)"
        )
        parser.add_argument(
            "--skip-bug-analyzer",
            action="store_true",
            help="Skip running bug_analyzer and use the provided --output XML file directly."
        )
        parser.add_argument(
            "--single-bug-xml",
            type=str,
            help="Path to a file containing a single <bug> element. Wraps it in a minimal bug_analysis_report and uses it as the XML input. Mutually exclusive with --skip-bug-analyzer."
        )

    def parse_args(self, args: Optional[Sequence[str]] = None) -> argparse.Namespace:
        parser = argparse.ArgumentParser(description=self.get_description())
        parser.add_argument(
            "--output",
            type=str,
            default="bug_analysis_report.xml",
            help="Output file path for the bug analysis report (default: bug_analysis_report.xml)"
        )
        parser.add_argument(
            "--debug",
            action="store_true",
            help="Run aider with --pretty and --stream flags for debugging"
        )
        parser.add_argument(
            "--working-tree",
            action="store_true",
            help="Analyze diff between working tree and HEAD (default: False)"
        )
        parser.add_argument(
            "--commit",
            type=str,
            help="Commit ID to analyze (optional, overrides working tree if provided)"
        )
        parser.add_argument(
            "--skip-bug-analyzer",
            action="store_true",
            help="Skip running bug_analyzer and use the provided --output XML file directly."
        )
        parser.add_argument(
            "--single-bug-xml",
            type=str,
            help="Path to a file containing a single <bug> element. Wraps it in a minimal bug_analysis_report and uses it as the XML input. Mutually exclusive with --skip-bug-analyzer."
        )
        parsed_args = parser.parse_args(args)
        if parsed_args.skip_bug_analyzer and parsed_args.single_bug_xml:
            parser.error("--skip-bug-analyzer and --single-bug-xml are mutually exclusive.")
        return parsed_args

    def wrap_single_bug_xml(self, bug_file: str, output_file: str) -> None:
        """Wrap a single <bug> element in a minimal <bug_analysis_report> XML structure and write to output_file."""
        try:
            with open(bug_file, 'r', encoding='utf-8') as f:
                bug_xml = f.read().strip()
            # Parse the bug element
            bug_elem = ET.fromstring(bug_xml)
            file_path_elem = bug_elem.find('file_path')
            file_path = file_path_elem.text.strip() if file_path_elem is not None and file_path_elem.text else None
            # Build the minimal bug_analysis_report
            report_elem = ET.Element('bug_analysis_report')
            affected_files_elem = ET.SubElement(report_elem, 'affected_files')
            if file_path:
                file_elem = ET.SubElement(affected_files_elem, 'file')
                file_elem.text = file_path
            bugs_elem = ET.SubElement(report_elem, 'bugs')
            bugs_elem.append(bug_elem)
            # Write to output_file
            tree = ET.ElementTree(report_elem)
            tree.write(output_file, encoding='utf-8', xml_declaration=True)
        except Exception as e:
            logger.error(f"Error wrapping single bug XML: {e}")
            raise

    def run(self) -> int:
        args = self.args if hasattr(self, 'args') and self.args is not None else self.parse_args()
        output_file = args.output
        debug = getattr(args, 'debug', False)
        working_tree = getattr(args, 'working_tree', False)
        commit = getattr(args, 'commit', None)
        skip_bug_analyzer = getattr(args, 'skip_bug_analyzer', False)
        single_bug_xml = getattr(args, 'single_bug_xml', None)

        # Step 0: If --single-bug-xml is provided, wrap it and use as XML input
        if single_bug_xml:
            logger.info(f"Wrapping single bug XML from {single_bug_xml} into {output_file}")
            try:
                self.wrap_single_bug_xml(single_bug_xml, output_file)
            except Exception:
                return 1
        # Step 1: Run bug_analyzer on working tree or commit, unless skipping or using single bug
        elif not skip_bug_analyzer:
            logger.info("Running bug_analyzer...")
            bug_analyzer_cmd = [
                "bug-analyzer",
                "--directory", "/src"
            ]
            if commit:
                bug_analyzer_cmd.extend(["--commit", commit])
            elif working_tree:
                bug_analyzer_cmd.append("--working-tree")
            if debug:
                bug_analyzer_cmd.append("--debug")
            bug_analyzer_cmd.extend(["--output", output_file])
            try:
                result = subprocess.run(bug_analyzer_cmd, capture_output=True, text=True)
                # Log bug_analyzer output with debug awareness
                for line in result.stdout.splitlines():
                    line_stripped = line.strip()
                    if 'DEBUG' in line_stripped:
                        logger.debug(f"[bug_analyzer debug] {line_stripped}")
                    elif 'INFO' in line_stripped:
                        logger.info(f"[bug_analyzer info] {line_stripped}")
                    elif 'WARNING' in line_stripped or 'WARN' in line_stripped:
                        logger.warning(f"[bug_analyzer warning] {line_stripped}")
                    elif 'ERROR' in line_stripped:
                        logger.error(f"[bug_analyzer error] {line_stripped}")
                    else:
                        logger.info(f"[bug_analyzer] {line_stripped}")
                for line in result.stderr.splitlines():
                    line_stripped = line.strip()
                    if 'DEBUG' in line_stripped:
                        logger.debug(f"[bug_analyzer debug] {line_stripped}")
                    elif 'INFO' in line_stripped:
                        logger.info(f"[bug_analyzer info] {line_stripped}")
                    elif 'WARNING' in line_stripped or 'WARN' in line_stripped:
                        logger.warning(f"[bug_analyzer warning] {line_stripped}")
                    elif 'ERROR' in line_stripped:
                        logger.error(f"[bug_analyzer error] {line_stripped}")
                    else:
                        logger.error(f"[bug_analyzer stderr] {line_stripped}")
                if result.returncode != 0:
                    logger.error(f"bug_analyzer failed: {result.stderr}")
                    return 1
                logger.info(f"bug_analyzer completed. Output written to {output_file}")
            except FileNotFoundError:
                logger.error("bug_analyzer not found. Ensure it is installed and importable.")
                return 1
            except Exception as e:
                logger.error(f"Error running bug_analyzer: {e}")
                return 1
        else:
            logger.info("Skipping bug_analyzer. Using pre-produced bug analysis report.")

        # Step 2: Feed XML output to aider
        xml_path = Path(output_file)
        if not xml_path.exists():
            logger.error(f"Bug analysis report not found at {output_file}")
            return 1

        # Extract file paths from the XML report
        file_paths = self.extract_file_paths(xml_path)
        if file_paths:
            logger.info(f"Found {len(file_paths)} file(s) in the bug analysis report: {', '.join(file_paths)}")
        else:
            logger.warning("No file paths found in the bug analysis report")

        logger.info(f"Feeding bug analysis report {output_file} to aider...")
        aider_cmd = [
            "aider",
            "--yes",
            "--message", self.get_default_message(),
            str(xml_path)
        ]

        # Add files to aider with --add flag
        for file_path in file_paths:
            aider_cmd.extend(["--add", file_path])

        if debug:
            aider_cmd.extend(["--pretty", "--stream"])
        try:
            process = subprocess.Popen(aider_cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
            if process.stdout:
                for line in iter(process.stdout.readline, ''):
                    line_stripped = line.strip()
                    if 'DEBUG' in line_stripped:
                        logger.debug(f"[aider debug] {line_stripped}")
                    else:
                        logger.info(f"[aider] {line_stripped}")
            if process.stderr:
                for line in iter(process.stderr.readline, ''):
                    line_stripped = line.strip()
                    if 'DEBUG' in line_stripped:
                        logger.debug(f"[aider debug] {line_stripped}")
                    else:
                        logger.error(f"[aider stderr] {line_stripped}")
            process.wait()
            if process.returncode == 0:
                logger.info("Aider completed successfully.")
                return 0
            else:
                logger.error(f"Aider failed with exit code {process.returncode}")
                return process.returncode
        except FileNotFoundError:
            logger.error("aider not found. Please install aider-chat.")
            return 1
        except Exception as e:
            logger.error(f"Error running aider: {e}")
            return 1


def main() -> int:
    processor = FixBugsProcessor()
    return processor.run()


if __name__ == "__main__":
    import sys

    sys.exit(main())
