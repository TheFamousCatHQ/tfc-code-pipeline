#!/usr/bin/env python3
"""
Script to find source files in a directory.

This script searches for source files of any programming language in a specified directory,
excluding dependencies, tests, and other non-core files.
"""

import argparse
import os
import sys
from pathlib import Path
from typing import List, Set


def parse_args() -> argparse.Namespace:
    """Parse command-line arguments.

    Returns:
        Parsed command-line arguments.
    """
    parser = argparse.ArgumentParser(description="Find source files in a directory")
    parser.add_argument(
        "--directory",
        type=str,
        required=True,
        help="Directory to search for source files"
    )
    return parser.parse_args()


def is_source_file(file_path: Path) -> bool:
    """Check if a file is a source file.

    Args:
        file_path: Path to the file.

    Returns:
        True if the file is a source file, False otherwise.
    """
    # Common source file extensions for various programming languages
    source_extensions = {
        # Python
        '.py', '.pyx', '.pyi',
        # JavaScript/TypeScript
        '.js', '.jsx', '.ts', '.tsx',
        # Java
        '.java',
        # C/C++
        '.c', '.cpp', '.cc', '.cxx', '.h', '.hpp', '.hxx',
        # C#
        '.cs',
        # Go
        '.go',
        # Ruby
        '.rb',
        # PHP
        '.php',
        # Swift
        '.swift',
        # Kotlin
        '.kt', '.kts',
        # Rust
        '.rs',
        # Scala
        '.scala',
        # Shell
        '.sh', '.bash',
        # HTML/CSS (sometimes considered source)
        '.html', '.htm', '.css',
        # Other
        '.r', '.pl', '.pm', '.lua', '.groovy', '.dart', '.elm'
    }

    return file_path.suffix.lower() in source_extensions


def should_skip_directory(dir_path: Path) -> bool:
    """Check if a directory should be skipped.

    Args:
        dir_path: Path to the directory.

    Returns:
        True if the directory should be skipped, False otherwise.
    """
    # Common directories to skip
    skip_dirs = {
        # Dependencies
        'node_modules', 'venv', '.venv', 'env', '.env', 'virtualenv', '.virtualenv',
        'vendor', 'bower_components', 'jspm_packages', 'packages',
        'target', 'build', 'dist', 'out', 'output', 'bin', 'obj',
        # Tests
        'test', 'tests', 'spec', 'specs', 'testing',
        # Version control
        '.git', '.svn', '.hg', '.bzr',
        # IDE and editor files
        '.idea', '.vscode', '.vs', '.eclipse', '.settings',
        # Cache and temporary files
        '__pycache__', '.cache', 'tmp', 'temp', '.tmp', '.temp',
        # Documentation
        'docs', 'doc', 'documentation',
        # Generated files
        'generated', 'gen', 'auto-generated',
        # Other
        '.github', '.gitlab', 'coverage', '.coverage', 'htmlcov'
    }

    # Check if the directory name should be skipped
    if dir_path.name.lower() in skip_dirs:
        return True

    # Check if any parent directory in the path should be skipped
    for part in dir_path.parts:
        if part.lower() in skip_dirs:
            return True

    return False


def find_source_files(directory: str) -> List[str]:
    """Find source files in a directory.

    Args:
        directory: Directory to search for source files.

    Returns:
        List of source files.
    """
    source_files = []
    dir_path = Path(directory).resolve()

    if not dir_path.exists():
        print(f"Error: Directory '{directory}' does not exist.", file=sys.stderr)
        return []

    if not dir_path.is_dir():
        print(f"Error: '{directory}' is not a directory.", file=sys.stderr)
        return []

    for root, dirs, files in os.walk(dir_path):
        # Skip directories that should be excluded
        dirs[:] = [d for d in dirs if not should_skip_directory(Path(root) / d)]

        for file in files:
            file_path = Path(root) / file
            if is_source_file(file_path):
                source_files.append(str(file_path))

    return source_files


def main() -> int:
    """Run the main script.

    Returns:
        Exit code (0 for success, non-zero for failure).
    """
    try:
        args = parse_args()
        source_files = find_source_files(args.directory)

        for file in source_files:
            print(file)

        return 0
    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())