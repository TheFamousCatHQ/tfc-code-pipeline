#!/usr/bin/env python3
"""
Script to find source files in a directory.

This script searches for source files of any programming language in a specified directory,
excluding dependencies, tests, and other non-core files.
"""

import argparse
import logging
import os
import sys
from pathlib import Path
from typing import List, Set

# Set up logging
logger = logging.getLogger(__name__)


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


def is_config_file(file_path: Path) -> bool:
    """Check if a file is a configuration file.

    Args:
        file_path: Path to the file.

    Returns:
        True if the file is a configuration file, False otherwise.
    """
    # Common configuration file names and patterns
    config_file_names = {
        # General config files
        'config.js', 'config.ts', 'config.json', 'config.yaml', 'config.yml',
        'config.toml', 'config.ini', 'config.xml', 'config.env',
        # Package managers
        'package.json', 'package-lock.json', 'yarn.lock', 'pnpm-lock.yaml',
        'composer.json', 'composer.lock', 'Gemfile', 'Gemfile.lock',
        'requirements.txt', 'pyproject.toml', 'poetry.lock', 'Pipfile', 'Pipfile.lock',
        # Build tools
        'webpack.config.js', 'rollup.config.js', 'vite.config.js', 'babel.config.js',
        'tsconfig.json', 'tslint.json', 'eslintrc.js', '.eslintrc.js', '.eslintrc.json',
        'jest.config.js', 'vitest.config.js', 'karma.conf.js',
        # CI/CD
        '.travis.yml', '.gitlab-ci.yml', '.github/workflows/main.yml',
        'Jenkinsfile', 'azure-pipelines.yml', 'bitbucket-pipelines.yml',
        # Docker
        'Dockerfile', 'docker-compose.yml', 'docker-compose.yaml',
        # Other
        '.env', '.env.example', '.env.local', '.env.development', '.env.production',
        '.gitignore', '.gitattributes', '.editorconfig', '.prettierrc', '.prettierrc.js',
        'README.md', 'LICENSE', 'CHANGELOG.md', 'CONTRIBUTING.md'
    }

    # Check if the file name matches a known config file
    if file_path.name in config_file_names:
        return True

    # Check for common config file patterns
    config_patterns = [
        # Config files with .config. in the name
        '.config.',
        # Files starting with dot
        '.eslintrc', '.babelrc', '.stylelintrc',
        # Common config file suffixes
        'rc.js', 'rc.json', 'rc.yaml', 'rc.yml',
        # Test config files
        'test.config.', 'jest.config.', 'vitest.config.', 'karma.config.',
        # Build config files
        'webpack.', 'rollup.', 'vite.', 'babel.', 'postcss.config.'
    ]

    for pattern in config_patterns:
        if pattern in file_path.name:
            return True

    return False


def is_dot_file(file_path: Path) -> bool:
    """Check if a file is a dot file (hidden file).

    Args:
        file_path: Path to the file.

    Returns:
        True if the file is a dot file, False otherwise.
    """
    # Check if the file name starts with a dot
    return file_path.name.startswith('.')


def is_test_file(file_path: Path) -> bool:
    """Check if a file is a test file.

    Args:
        file_path: Path to the file.

    Returns:
        True if the file is a test file, False otherwise.
    """
    # Common test file patterns
    test_patterns = [
        'test_', 'tests_', '_test', '_tests',
        'spec_', 'specs_', '_spec', '_specs',
        '.test.', '.spec.', '-test.', '-spec.'
    ]

    # Check if the file name starts with or contains test patterns
    file_name = file_path.stem.lower()
    full_name = file_path.name.lower()
    for pattern in test_patterns:
        if pattern in file_name or pattern in full_name:
            return True

    # Check if the file is in a test directory
    for part in file_path.parts:
        if part.lower() in {'test', 'tests', 'spec', 'specs', 'testing'}:
            return True
        # Check for integration test directories
        if 'tests_integration' in part.lower() or 'integration_tests' in part.lower():
            return True

    return False


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

    # First check if it's a config file - if so, it's not a source file
    if is_config_file(file_path):
        return False

    # Check if it's a test file - if so, it's not a source file
    if is_test_file(file_path):
        return False

    # Check if it's a dot file - if so, it's not a source file
    if is_dot_file(file_path):
        return False

    # Check if it's in a dot directory - if so, it's not a source file
    for part in file_path.parts:
        if part.startswith('.'):
            return False

    # Otherwise, check if it has a source file extension
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

    # Check if the directory name starts with a dot (hidden directory)
    if dir_path.name.startswith('.'):
        return True

    # Check if any parent directory in the path should be skipped
    for part in dir_path.parts:
        if part.lower() in skip_dirs:
            return True
        # Check if any parent directory starts with a dot
        if part.startswith('.'):
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
        logger.error(f"Error: Directory '{directory}' does not exist.")
        return []

    if not dir_path.is_dir():
        logger.error(f"Error: '{directory}' is not a directory.")
        return []

    for root, dirs, files in os.walk(dir_path):
        # Skip directories that should be excluded
        dirs[:] = [d for d in dirs if not should_skip_directory(Path(root) / d)]

        for file in files:
            file_path = Path(root) / file
            if is_source_file(file_path):
                source_files.append(str(file_path))

    return source_files


def configure_logging(verbose: bool = False):
    """Configure logging for the find_source_files module.

    Args:
        verbose: Whether to enable verbose (DEBUG) logging.
    """
    try:
        # Try importing directly (for Docker/installed package)
        from logging_utils import configure_logging as setup_logging
    except ImportError:
        # Fall back to src-prefixed import (for local development)
        from src.logging_utils import configure_logging as setup_logging

    # Configure logging using the centralized function
    setup_logging(verbose, module_name="find_source_files")


def main() -> int:
    """Run the main script.

    Returns:
        Exit code (0 for success, non-zero for failure).
    """
    try:
        args = parse_args()

        # Configure logging
        configure_logging(getattr(args, 'verbose', False))

        source_files = find_source_files(args.directory)

        for file in source_files:
            logger.info(file)

        return 0
    except Exception as e:
        logger.error(f"Error: {e}")
        return 1


if __name__ == "__main__":
    sys.exit(main())
