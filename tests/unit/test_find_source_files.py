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
    is_config_file,
    is_test_file,
    is_dot_file,
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

    def test_is_config_file(self):
        """Test is_config_file with various file names."""
        # Test common configuration files
        self.assertTrue(is_config_file(Path("config.js")))
        self.assertTrue(is_config_file(Path("webpack.config.js")))
        self.assertTrue(is_config_file(Path("vitest.config.js")))
        self.assertTrue(is_config_file(Path("jest.config.js")))
        self.assertTrue(is_config_file(Path("babel.config.js")))
        self.assertTrue(is_config_file(Path("tsconfig.json")))
        self.assertTrue(is_config_file(Path("package.json")))
        self.assertTrue(is_config_file(Path("pyproject.toml")))
        self.assertTrue(is_config_file(Path(".eslintrc.js")))
        self.assertTrue(is_config_file(Path(".prettierrc")))
        self.assertTrue(is_config_file(Path("Dockerfile")))
        self.assertTrue(is_config_file(Path(".env")))
        self.assertTrue(is_config_file(Path(".gitignore")))

        # Test files that are not configuration files
        self.assertFalse(is_config_file(Path("app.js")))
        self.assertFalse(is_config_file(Path("main.py")))
        self.assertFalse(is_config_file(Path("index.ts")))
        self.assertFalse(is_config_file(Path("component.jsx")))
        self.assertFalse(is_config_file(Path("styles.css")))
        self.assertFalse(is_config_file(Path("data.json")))

    def test_is_dot_file(self):
        """Test is_dot_file with various file names."""
        # Test files that should be identified as dot files
        self.assertTrue(is_dot_file(Path(".gitignore")))
        self.assertTrue(is_dot_file(Path(".env")))
        self.assertTrue(is_dot_file(Path(".eslintrc.js")))
        self.assertTrue(is_dot_file(Path(".prettierrc")))
        self.assertTrue(is_dot_file(Path(".hidden_file")))
        self.assertTrue(is_dot_file(Path(".config")))

        # Test files that should not be identified as dot files
        self.assertFalse(is_dot_file(Path("file.py")))
        self.assertFalse(is_dot_file(Path("app.js")))
        self.assertFalse(is_dot_file(Path("index.ts")))
        self.assertFalse(is_dot_file(Path("component.tsx")))
        self.assertFalse(is_dot_file(Path("file.with.dots.py")))
        self.assertFalse(is_dot_file(Path("file_with_no_extension")))

    def test_is_test_file(self):
        """Test is_test_file with various file names."""
        # Test files that should be identified as test files
        self.assertTrue(is_test_file(Path("test_file.py")))
        self.assertTrue(is_test_file(Path("tests_file.py")))
        self.assertTrue(is_test_file(Path("file_test.py")))
        self.assertTrue(is_test_file(Path("file_tests.py")))
        self.assertTrue(is_test_file(Path("file.test.js")))
        self.assertTrue(is_test_file(Path("file.spec.js")))
        self.assertTrue(is_test_file(Path("file-test.js")))
        self.assertTrue(is_test_file(Path("file-spec.js")))

        # Test files in test directories
        self.assertTrue(is_test_file(Path("test/file.py")))
        self.assertTrue(is_test_file(Path("tests/file.py")))
        self.assertTrue(is_test_file(Path("spec/file.js")))
        self.assertTrue(is_test_file(Path("specs/file.js")))
        self.assertTrue(is_test_file(Path("testing/file.py")))
        self.assertTrue(is_test_file(Path("/path/to/test/file.py")))

        # Test files in integration test directories
        self.assertTrue(is_test_file(Path("tests_integration/file.py")))
        self.assertTrue(is_test_file(Path("tests_integration/mysql/custom_provider.py")))
        self.assertTrue(is_test_file(Path("/pynonymizer/tests_integration/mysql/custom_provider.py")))
        self.assertTrue(is_test_file(Path("integration_tests/file.py")))
        self.assertTrue(is_test_file(Path("path/to/integration_tests/file.py")))

        # Test files that should not be identified as test files
        self.assertFalse(is_test_file(Path("file.py")))
        self.assertFalse(is_test_file(Path("app.js")))
        self.assertFalse(is_test_file(Path("index.ts")))
        self.assertFalse(is_test_file(Path("component.tsx")))
        self.assertFalse(is_test_file(Path("testing.py")))  # "testing" in filename but not matching pattern
        self.assertFalse(is_test_file(Path("testfile.py")))  # "test" in filename but not matching pattern

    def test_is_source_file(self):
        """Test is_source_file with various file extensions."""
        # Test Python files
        self.assertTrue(is_source_file(Path("file.py")))
        self.assertTrue(is_source_file(Path("file.pyx")))
        self.assertTrue(is_source_file(Path("file.pyi")))

        # Test JavaScript/TypeScript files
        self.assertTrue(is_source_file(Path("app.js")))
        self.assertTrue(is_source_file(Path("component.jsx")))
        self.assertTrue(is_source_file(Path("index.ts")))
        self.assertTrue(is_source_file(Path("component.tsx")))

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

        # Test configuration files (should not be considered source files)
        self.assertFalse(is_source_file(Path("config.js")))
        self.assertFalse(is_source_file(Path("webpack.config.js")))
        self.assertFalse(is_source_file(Path("vitest.config.js")))
        self.assertFalse(is_source_file(Path("jest.config.js")))
        self.assertFalse(is_source_file(Path("babel.config.js")))
        self.assertFalse(is_source_file(Path("tsconfig.json")))
        self.assertFalse(is_source_file(Path("package.json")))
        self.assertFalse(is_source_file(Path("pyproject.toml")))
        self.assertFalse(is_source_file(Path(".eslintrc.js")))

        # Test test files (should not be considered source files)
        self.assertFalse(is_source_file(Path("test_file.py")))
        self.assertFalse(is_source_file(Path("file_test.py")))
        self.assertFalse(is_source_file(Path("file.test.js")))
        self.assertFalse(is_source_file(Path("file.spec.js")))
        self.assertFalse(is_source_file(Path("test/file.py")))
        self.assertFalse(is_source_file(Path("tests/file.py")))

        # Test dot files (should not be considered source files)
        self.assertFalse(is_source_file(Path(".gitignore")))
        self.assertFalse(is_source_file(Path(".env")))
        self.assertFalse(is_source_file(Path(".eslintrc.js")))
        self.assertFalse(is_source_file(Path(".prettierrc")))
        self.assertFalse(is_source_file(Path(".hidden_file.py")))

        # Test files in dot directories (should not be considered source files)
        self.assertFalse(is_source_file(Path(".hidden_dir/file.py")))
        self.assertFalse(is_source_file(Path("path/to/.hidden_dir/file.py")))
        self.assertFalse(is_source_file(Path(".git/file.py")))
        self.assertFalse(is_source_file(Path(".vscode/settings.json")))

    def test_should_skip_directory(self):
        """Test should_skip_directory with various directory names."""
        # Test directories that should be skipped
        self.assertTrue(should_skip_directory(Path("node_modules")))
        self.assertTrue(should_skip_directory(Path("venv")))
        self.assertTrue(should_skip_directory(Path(".venv")))
        self.assertTrue(should_skip_directory(Path("tests")))
        self.assertTrue(should_skip_directory(Path(".git")))
        self.assertTrue(should_skip_directory(Path(".idea")))

        # Test dot directories (should be skipped)
        self.assertTrue(should_skip_directory(Path(".hidden_dir")))
        self.assertTrue(should_skip_directory(Path(".config")))
        self.assertTrue(should_skip_directory(Path(".cache")))
        self.assertTrue(should_skip_directory(Path(".local")))

        # Test directories that should not be skipped
        self.assertFalse(should_skip_directory(Path("src")))
        self.assertFalse(should_skip_directory(Path("app")))
        self.assertFalse(should_skip_directory(Path("lib")))
        self.assertFalse(should_skip_directory(Path("core")))

        # Test nested directories
        self.assertTrue(should_skip_directory(Path("/path/to/node_modules/subdir")))
        self.assertTrue(should_skip_directory(Path("/path/to/tests/subdir")))
        self.assertTrue(should_skip_directory(Path("/path/to/.hidden_dir/subdir")))
        self.assertTrue(should_skip_directory(Path("/path/to/.git/subdir")))
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
                "app.js",
                "file3.java",
                "subdir/file4.cpp"
            ]

            # Create some non-source files
            non_source_files = [
                "file5.txt",
                "file6.md",
                "subdir/file7.json"
            ]

            # Create some config files (should be skipped even though they have source extensions)
            config_files = [
                "webpack.config.js",
                "vitest.config.js",
                "jest.config.js",
                "babel.config.js",
                "tsconfig.json",
                "package.json",
                "pyproject.toml",
                ".eslintrc.js"
            ]

            # Create some test files (should be skipped even though they have source extensions)
            test_files = [
                "test_file.py",
                "file_test.py",
                "file.test.js",
                "file.spec.js",
                "subdir/test_subfile.py"
            ]

            # Create some dot files (should be skipped even though they have source extensions)
            dot_files = [
                ".gitignore",
                ".env",
                ".eslintrc.js",
                ".prettierrc",
                ".hidden_file.py",
                ".config/settings.py",
                ".vscode/launch.json"
            ]

            # Create the files
            for file_path in source_files_to_create + non_source_files + config_files + test_files + dot_files:
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

            # Check that config files are not in the result (even though some have .js extension)
            for file_path in config_files:
                full_path = str(Path(temp_dir) / file_path)
                self.assertNotIn(full_path, found_files)

            # Check that test files are not in the result (even though they have source extensions)
            for file_path in test_files:
                full_path = str(Path(temp_dir) / file_path)
                self.assertNotIn(full_path, found_files)

            # Check that dot files are not in the result (even though some have source extensions)
            for file_path in dot_files:
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
                "venv/file6.js",
                # Add dot directories
                ".hidden_dir/file7.py",
                ".config/file8.js",
                ".vscode/file9.py",
                "path/to/.hidden_subdir/file10.js"
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
