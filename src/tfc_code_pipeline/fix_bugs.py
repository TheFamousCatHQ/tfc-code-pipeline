"""
Processor to run bug_analyzer and then feed its XML output to aider to fix the bugs.
"""

import argparse
import subprocess
from pathlib import Path
from typing import Optional, Sequence

from code_processor import CodeProcessor
from logging_utils import get_logger

logger = get_logger("tfc-code-pipeline.fix_bugs")

class FixBugsProcessor(CodeProcessor):
    """Processor to run bug_analyzer and then feed its XML output to aider to fix the bugs."""

    def get_default_message(self) -> str:
        """Get the default message to pass to aider."""
        return (
            "Here is a bug analysis report in XML format. For each bug, please fix the code in the specified file and line. "
            "Apply the suggested fix if possible, or otherwise address the described issue. "
            "Do not make unrelated changes."
        )

    def get_description(self) -> str:
        return "Run bug_analyzer, then feed its XML output to aider to fix the bugs."

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
        return parser.parse_args(args)

    def run(self) -> int:
        args = self.args if hasattr(self, 'args') and self.args is not None else self.parse_args()
        output_file = args.output
        debug = getattr(args, 'debug', False)
        working_tree = getattr(args, 'working_tree', False)

        # Step 1: Run bug_analyzer on working tree or commit
        logger.info("Running bug_analyzer...")
        bug_analyzer_cmd = [
            "bug-analyzer",
            "--directory", "."
        ]
        if working_tree:
            bug_analyzer_cmd.append("--working-tree")
        bug_analyzer_cmd.extend(["--output", output_file])
        try:
            result = subprocess.run(bug_analyzer_cmd, capture_output=True, text=True)
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

        # Step 2: Feed XML output to aider
        xml_path = Path(output_file)
        if not xml_path.exists():
            logger.error(f"Bug analysis report not found at {output_file}")
            return 1
        logger.info(f"Feeding bug analysis report {output_file} to aider...")
        aider_cmd = [
            "aider",
            "--yes",
            "--message", self.get_default_message(),
            str(xml_path)
        ]
        if debug:
            aider_cmd.extend(["--pretty", "--stream"])
        try:
            process = subprocess.Popen(aider_cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
            if process.stdout:
                for line in iter(process.stdout.readline, ''):
                    logger.info(f"[aider] {line.strip()}")
            if process.stderr:
                for line in iter(process.stderr.readline, ''):
                    logger.error(f"[aider stderr] {line.strip()}")
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