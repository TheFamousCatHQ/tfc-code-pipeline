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