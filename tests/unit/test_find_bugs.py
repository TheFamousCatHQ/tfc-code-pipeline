"""Tests for the find_bugs module.

This module contains tests for the find_bugs script, which analyzes source files
to identify potential bugs and outputs the results as JSON.
"""

import json
import os
import sys
import unittest
from pathlib import Path
from unittest.mock import patch, MagicMock
from tempfile import TemporaryDirectory

# Add the src directory to the Python path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent / 'src'))

# Import the module to test
from find_bugs import FindBugsProcessor, main


class TestFindBugsProcessor(unittest.TestCase):
    """Tests for the FindBugsProcessor class."""

    def test_get_default_message(self):
        """Test that get_default_message returns the expected message."""
        processor = FindBugsProcessor()
        message = processor.get_default_message()
        self.assertIn("analyze this code and identify potential bugs", message)
        self.assertIn("severity", message)
        self.assertIn("confidence", message)

    def test_get_description(self):
        """Test that get_description returns the expected description."""
        processor = FindBugsProcessor()
        description = processor.get_description()
        self.assertIn("Find potential bugs", description)
        self.assertIn("JSON", description)

    @patch('subprocess.run')
    @patch('find_source_files.find_source_files')
    def test_process_files(self, mock_find_files, mock_run):
        """Test that process_files processes files and generates JSON output."""
        # Set up mocks
        mock_find_files.return_value = ['file1.py', 'file2.py']
        mock_process = MagicMock()
        mock_process.stdout = "Line 10: This is a potential bug (severity: high, confidence: medium)"
        mock_run.return_value = mock_process

        # Create a temporary directory for the output
        with TemporaryDirectory() as temp_dir:
            # Create processor and process files
            processor = FindBugsProcessor()
            processed_files = processor.process_files(temp_dir)

            # Check that the expected files were processed
            self.assertEqual(processed_files, ['file1.py', 'file2.py'])

            # Check that the JSON file was created
            json_path = os.path.join(temp_dir, 'bugs_report.json')
            self.assertTrue(os.path.exists(json_path))

            # Check the content of the JSON file
            with open(json_path, 'r') as f:
                bugs_data = json.load(f)
                self.assertIsInstance(bugs_data, list)
                # We should have at least one bug per file
                self.assertGreaterEqual(len(bugs_data), 2)

    @patch('find_bugs.FindBugsProcessor.run')
    def test_main(self, mock_run):
        """Test that main calls the processor's run method."""
        mock_run.return_value = 0
        result = main()
        self.assertEqual(result, 0)
        mock_run.assert_called_once()


if __name__ == '__main__':
    unittest.main()
