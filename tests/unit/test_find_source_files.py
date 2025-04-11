"""Tests for the find_source_files module.

This module contains tests for the find_source_files script, which searches for source files
in a directory while excluding dependencies, tests, and other non-core files.
"""

import os
import sys
import unittest
from pathlib import Path
from unittest.mock import patch, MagicMock
from tempfile import TemporaryDirectory
from argparse import Namespace

# Add the src directory to the Python path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent / 'src'))

# Import the module to test
from find_source_files import (
    parse_args,
    is_source_file,
    should_skip_directory,
    find_source_files,
    main
)


class TestFindSourceFiles(unittest.TestCase):
    """Tests for the find_source_files functions."""

    def test_parse_args(self):
        """Test parse_args with directory argument."""
        with patch('sys.argv', ['find_source_files.py', '--directory', '/path/to/dir']):
            with patch('argparse.ArgumentParser.parse_args') as mock_parse_args:
                mock_parse_args.return_value = Namespace(directory="/path/to/dir")
                args = parse_args()
                self.assertEqual(args.directory, "/path/to/dir")

    def test_is_source_file(self):
        """Test is_source_file with various file extensions."""
        # Test Python files
        self.assertTrue(is_source_file(Path("file.py")))
        self.assertTrue(is_source_file(Path("file.pyx")))
        self.assertTrue(is_source_file(Path("file.pyi")))

        # Test JavaScript/TypeScript files
        self.assertTrue(is_source_file(Path("file.js")))
        self.assertTrue(is_source_file(Path("file.jsx")))
        self.assertTrue(is_source_file(Path("file.ts")))
        self.assertTrue(is_source_file(Path("file.tsx")))

        # Test other common source files
        self.assertTrue(is_source_file(Path("file.java")))
        self.assertTrue(is_source_file(Path("file.c")))
        self.assertTrue(is_source_file(Path("file.cpp")))
        self.assertTrue(is_source_file(Path("file.go")))

        # Test non-source files
        self.assertFalse(is_source_file(Path("file.txt")))
        self.assertFalse(is_source_file(Path("file.md")))
        self.assertFalse(is_source_file(Path("file.json")))
        self.assertFalse(is_source_file(Path("file.csv")))

    def test_should_skip_directory(self):
        """Test should_skip_directory with various directory names."""
        # Test directories that should be skipped
        self.assertTrue(should_skip_directory(Path("node_modules")))
        self.assertTrue(should_skip_directory(Path("venv")))
        self.assertTrue(should_skip_directory(Path(".venv")))
        self.assertTrue(should_skip_directory(Path("tests")))
        self.assertTrue(should_skip_directory(Path(".git")))
        self.assertTrue(should_skip_directory(Path(".idea")))

        # Test directories that should not be skipped
        self.assertFalse(should_skip_directory(Path("src")))
        self.assertFalse(should_skip_directory(Path("app")))
        self.assertFalse(should_skip_directory(Path("lib")))
        self.assertFalse(should_skip_directory(Path("core")))

        # Test nested directories
        self.assertTrue(should_skip_directory(Path("/path/to/node_modules/subdir")))
        self.assertTrue(should_skip_directory(Path("/path/to/tests/subdir")))
        self.assertFalse(should_skip_directory(Path("/path/to/src/subdir")))

    def test_find_source_files_empty_directory(self):
        """Test find_source_files with an empty directory."""
        with TemporaryDirectory() as temp_dir:
            source_files = find_source_files(temp_dir)
            self.assertEqual(source_files, [])

    def test_find_source_files_with_source_files(self):
        """Test find_source_files with a directory containing source files."""
        with TemporaryDirectory() as temp_dir:
            # Create some source files
            source_files_to_create = [
                "file1.py",
                "file2.js",
                "file3.java",
                "subdir/file4.cpp"
            ]

            # Create some non-source files
            non_source_files = [
                "file5.txt",
                "file6.md",
                "subdir/file7.json"
            ]

            # Create the files
            for file_path in source_files_to_create + non_source_files:
                full_path = Path(temp_dir) / file_path
                full_path.parent.mkdir(parents=True, exist_ok=True)
                full_path.touch()

            # Find source files
            found_files = find_source_files(temp_dir)

            # Check that all source files are found
            self.assertEqual(len(found_files), len(source_files_to_create))

            # Check that each source file is in the result
            for file_path in source_files_to_create:
                full_path = str(Path(temp_dir) / file_path)
                # On macOS, temporary directories might have /private prefix
                found = False
                for found_file in found_files:
                    if found_file.endswith(file_path):
                        found = True
                        break
                self.assertTrue(found, f"File {file_path} not found in results")

            # Check that non-source files are not in the result
            for file_path in non_source_files:
                full_path = str(Path(temp_dir) / file_path)
                self.assertNotIn(full_path, found_files)

    def test_find_source_files_with_skip_directories(self):
        """Test find_source_files with directories that should be skipped."""
        with TemporaryDirectory() as temp_dir:
            # Create some source files in regular directories
            regular_source_files = [
                "src/file1.py",
                "lib/file2.js"
            ]

            # Create some source files in directories that should be skipped
            skip_dir_source_files = [
                "node_modules/file3.py",
                "tests/file4.js",
                ".git/file5.py",
                "venv/file6.js"
            ]

            # Create the files
            for file_path in regular_source_files + skip_dir_source_files:
                full_path = Path(temp_dir) / file_path
                full_path.parent.mkdir(parents=True, exist_ok=True)
                full_path.touch()

            # Find source files
            found_files = find_source_files(temp_dir)

            # Check that only regular source files are found
            self.assertEqual(len(found_files), len(regular_source_files))

            # Check that each regular source file is in the result
            for file_path in regular_source_files:
                # On macOS, temporary directories might have /private prefix
                found = False
                for found_file in found_files:
                    if found_file.endswith(file_path):
                        found = True
                        break
                self.assertTrue(found, f"File {file_path} not found in results")

            # Check that source files in skip directories are not in the result
            for file_path in skip_dir_source_files:
                full_path = str(Path(temp_dir) / file_path)
                self.assertNotIn(full_path, found_files)

    def test_find_source_files_nonexistent_directory(self):
        """Test find_source_files with a nonexistent directory."""
        with patch('sys.stderr', new=MagicMock()):
            source_files = find_source_files("/nonexistent/directory")
            self.assertEqual(source_files, [])

    def test_find_source_files_not_a_directory(self):
        """Test find_source_files with a path that is not a directory."""
        with TemporaryDirectory() as temp_dir:
            # Create a file
            file_path = Path(temp_dir) / "file.txt"
            file_path.touch()

            # Try to find source files in the file
            with patch('sys.stderr', new=MagicMock()):
                source_files = find_source_files(str(file_path))
                self.assertEqual(source_files, [])

    @patch('argparse.ArgumentParser.parse_args')
    @patch('find_source_files.find_source_files')
    def test_main_success(self, mock_find_source_files, mock_parse_args):
        """Test main function with successful execution."""
        # Setup mocks
        mock_parse_args.return_value = Namespace(directory="/path/to/dir")
        mock_find_source_files.return_value = ["/path/to/dir/file1.py", "/path/to/dir/file2.js"]

        # Redirect stdout to capture output
        with patch('sys.stdout', new=MagicMock()) as mock_stdout:
            result = main()

            # Verify the result
            self.assertEqual(result, 0)
            mock_parse_args.assert_called_once()
            mock_find_source_files.assert_called_once_with("/path/to/dir")

            # Verify that print was called for each file
            # Note: print() calls write() multiple times, so we check if the file paths are in the calls
            calls = [call[0][0] for call in mock_stdout.write.call_args_list]
            self.assertTrue(any("/path/to/dir/file1.py" in call for call in calls), "file1.py not printed")
            self.assertTrue(any("/path/to/dir/file2.js" in call for call in calls), "file2.js not printed")

    @patch('argparse.ArgumentParser.parse_args')
    def test_main_exception(self, mock_parse_args):
        """Test main function with an exception."""
        # Setup mocks to raise an exception
        mock_parse_args.side_effect = Exception("Test exception")

        # Redirect stderr to capture error output
        with patch('sys.stderr', new=MagicMock()) as mock_stderr:
            result = main()

            # Verify the result
            self.assertEqual(result, 1)
            mock_parse_args.assert_called_once()

            # Check that the error message was printed to stderr
            # Note: print() calls write() multiple times, so we check if the error message is in the calls
            calls = [call[0][0] for call in mock_stderr.write.call_args_list]
            self.assertTrue(any("Error: Test exception" in call for call in calls), "Error message not printed")


if __name__ == "__main__":
    unittest.main()
