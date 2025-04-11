"""Tests for the main module.

This module contains tests for the main functionality of the TFC Test Writer Aider.
"""

import os
import subprocess
import unittest
from pathlib import Path
from typing import Any, Dict, List, Optional, Union, cast
from unittest.mock import patch, MagicMock

# Local application imports
from tfc_test_writer_aider.main import main


class TestMain(unittest.TestCase):
    """Tests for the main function."""

    @patch('subprocess.run')
    @patch('pathlib.Path.exists')
    @patch('tfc_test_writer_aider.main.load_dotenv', autospec=True)
    def test_main_success(self, mock_load_dotenv, mock_exists, mock_run):
        """Test the main function when Docker command succeeds."""
        # Setup the mocks
        mock_exists.return_value = True  # Pretend .env file exists
        mock_result = MagicMock()
        mock_result.returncode = 0
        mock_run.return_value = mock_result

        # Set some test environment variables
        test_env = {
            'TEST_VAR1': 'value1',
            'TEST_VAR2': 'value2',
            'PATH': '/usr/bin:/bin'  # Common environment variable
        }

        with patch.dict(os.environ, test_env, clear=True):
            # Call the main function
            result = main()

            # Verify the result
            self.assertEqual(result, 0)

            # Verify that load_dotenv was called
            mock_load_dotenv.assert_called_once()

            # Verify that subprocess.run was called with the correct arguments
            mock_run.assert_called_once()
            args, kwargs = mock_run.call_args
            docker_cmd = args[0]

            # Check that we're using Python 3.12
            self.assertIn("python:3.12-slim", docker_cmd)

            # Check that we're installing aider and running it with the message "Hello"
            bash_cmd = docker_cmd[-1]
            self.assertIn("pip install aider-chat", bash_cmd)
            self.assertIn("aider --message \"Hello\"", bash_cmd)

            # Check that environment variables are passed to Docker
            for key, value in test_env.items():
                self.assertIn(f"-e", docker_cmd)
                self.assertIn(f"{key}={value}", docker_cmd)

    @patch('subprocess.run')
    @patch('pathlib.Path.exists')
    def test_main_docker_error(self, mock_exists, mock_run):
        """Test the main function when Docker command fails."""
        # Setup the mocks
        mock_exists.return_value = False  # Pretend .env file doesn't exist
        mock_run.side_effect = subprocess.CalledProcessError(1, "docker run")

        # Call the main function
        result = main()

        # Verify the result
        self.assertEqual(result, 1)

    @patch('subprocess.run')
    @patch('pathlib.Path.exists')
    def test_main_no_env_file(self, mock_exists, mock_run):
        """Test the main function when .env file doesn't exist."""
        # Setup the mocks
        mock_exists.return_value = False  # Pretend .env file doesn't exist
        mock_result = MagicMock()
        mock_result.returncode = 0
        mock_run.return_value = mock_result

        # Set some test environment variables
        test_env = {'TEST_VAR': 'test_value'}

        with patch.dict(os.environ, test_env, clear=True):
            # Call the main function
            result = main()

            # Verify the result
            self.assertEqual(result, 0)

            # Verify that subprocess.run was called with the correct arguments
            mock_run.assert_called_once()
            args, kwargs = mock_run.call_args
            docker_cmd = args[0]

            # Check that environment variables are still passed to Docker
            # even without a .env file
            self.assertIn("-e", docker_cmd)
            self.assertIn("TEST_VAR=test_value", docker_cmd)

    @patch('subprocess.run')
    @patch('pathlib.Path.exists')
    @patch('builtins.open', new_callable=unittest.mock.mock_open)
    @patch('pathlib.Path.unlink')
    def test_main_build_only(self, mock_unlink, mock_open, mock_exists, mock_run):
        """Test the main function with build_only=True."""
        # Setup the mocks
        mock_exists.return_value = False  # Pretend .env file doesn't exist
        mock_result = MagicMock()
        mock_result.returncode = 0
        mock_run.return_value = mock_result

        # Call the main function with build_only=True
        result = main(build_only=True)

        # Verify the result
        self.assertEqual(result, 0)

        # Verify that a Dockerfile was created
        mock_open.assert_called_once()
        file_handle = mock_open()
        file_content = file_handle.write.call_args[0][0]
        self.assertIn("FROM python:3.12-slim", file_content)
        self.assertIn("RUN pip install --no-cache-dir aider-chat", file_content)
        self.assertIn("ENTRYPOINT [\"aider\"]", file_content)

        # Verify that the Docker build command was run
        mock_run.assert_called_once()
        args, kwargs = mock_run.call_args
        docker_cmd = args[0]
        self.assertEqual(docker_cmd[0], "docker")
        self.assertEqual(docker_cmd[1], "build")
        self.assertIn("-t", docker_cmd)
        self.assertIn("tfc-test-writer-aider:python3.12", docker_cmd)

        # Verify that the temporary Dockerfile was removed
        mock_unlink.assert_called_once()
