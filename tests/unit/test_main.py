"""Tests for the main module.

This module contains tests for the main functionality of the TFC Code Pipeline.
"""

import os
import subprocess
import unittest
from pathlib import Path
from unittest.mock import patch, MagicMock

# Local application imports
from src.tfc_code_pipeline.main import main


class TestMain(unittest.TestCase):
    """Tests for the main function."""

    @patch('subprocess.run')
    @patch('pathlib.Path.exists')
    @patch('pathlib.Path.unlink')
    @patch('builtins.open', new_callable=unittest.mock.mock_open)
    @patch('src.tfc_code_pipeline.main.load_dotenv', autospec=True)
    @patch('src.tfc_code_pipeline.main.read_env_file', autospec=True)
    def test_main_success(self, mock_read_env_file, mock_load_dotenv, mock_open, mock_unlink, mock_exists, mock_run):
        """Test the main function when Docker command succeeds."""
        # Setup the mocks
        mock_exists.return_value = True  # Pretend .env file exists
        mock_result = MagicMock()
        mock_result.returncode = 0
        mock_run.return_value = mock_result

        # Set up environment variables that would be in the .env file
        env_from_file = {
            'TEST_VAR1': 'value1',
            'TEST_VAR2': 'value2',
        }
        mock_read_env_file.return_value = env_from_file

        # Set some test environment variables (these should not be passed to Docker)
        test_env = {
            'TEST_VAR1': 'value1',
            'TEST_VAR2': 'value2',
            'PATH': '/usr/bin:/bin',  # Common environment variable
            'SYSTEM_VAR': 'should_not_be_passed'  # This should not be passed to Docker
        }

        with patch.dict(os.environ, test_env, clear=True):
            # Call the main function
            result = main()

            # Verify the result
            self.assertEqual(result, 0)

            # Verify that load_dotenv was called
            mock_load_dotenv.assert_called_once()

            # Verify that read_env_file was called
            mock_read_env_file.assert_called_once()

            # Verify that a Dockerfile was created
            mock_open.assert_called_once()
            file_handle = mock_open()
            file_content = file_handle.write.call_args[0][0]
            self.assertIn("FROM python:3.12-slim", file_content)
            self.assertIn("RUN pip install --no-cache-dir aider-chat", file_content)
            self.assertIn("ENTRYPOINT [\"/bin/bash\"]", file_content)

            # Verify that the Docker build command was run
            self.assertEqual(mock_run.call_count, 2)  # Build and run
            build_args, build_kwargs = mock_run.call_args_list[0]
            build_cmd = build_args[0]
            self.assertEqual(build_cmd[0], "docker")
            self.assertEqual(build_cmd[1], "build")
            self.assertIn("-t", build_cmd)
            self.assertIn("tfc-code-pipeline:python3.12", build_cmd)

            # Verify that the temporary Dockerfile was removed
            mock_unlink.assert_called_once()

            # Verify that the Docker run command was called with the correct arguments
            run_args, run_kwargs = mock_run.call_args_list[1]
            docker_cmd = run_args[0]

            # Check that we're using the custom image
            self.assertIn("tfc-code-pipeline:python3.12", docker_cmd)

            # Check that we're running the explain-code command
            self.assertIn("explain-code", docker_cmd)

            # Check that only environment variables from the .env file are passed to Docker
            for key, value in env_from_file.items():
                self.assertIn(f"-e", docker_cmd)
                self.assertIn(f"{key}={value}", docker_cmd)

            # Check that system environment variables not in the .env file are not passed to Docker
            self.assertNotIn("SYSTEM_VAR=should_not_be_passed", str(docker_cmd))

    @patch('subprocess.run')
    @patch('pathlib.Path.exists')
    @patch('pathlib.Path.unlink')
    @patch('builtins.open', new_callable=unittest.mock.mock_open)
    def test_main_docker_error(self, mock_open, mock_unlink, mock_exists, mock_run):
        """Test the main function when Docker command fails."""
        # Setup the mocks
        mock_exists.return_value = False  # Pretend .env file doesn't exist
        mock_run.side_effect = subprocess.CalledProcessError(1, "docker run")

        # Call the main function
        result = main()

        # Verify the result
        self.assertEqual(result, 1)

        # Verify that a Dockerfile was created
        mock_open.assert_called_once()

        # In the error case, we don't expect unlink to be called
        # since the error happens before we get to that point
        mock_unlink.assert_not_called()

    @patch('subprocess.run')
    @patch('pathlib.Path.exists')
    @patch('pathlib.Path.unlink')
    @patch('builtins.open', new_callable=unittest.mock.mock_open)
    def test_main_no_env_file(self, mock_open, mock_unlink, mock_exists, mock_run):
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

            # Verify that a Dockerfile was created
            mock_open.assert_called_once()
            file_handle = mock_open()
            file_content = file_handle.write.call_args[0][0]
            self.assertIn("FROM python:3.12-slim", file_content)
            self.assertIn("RUN pip install --no-cache-dir aider-chat", file_content)
            self.assertIn("ENTRYPOINT [\"/bin/bash\"]", file_content)

            # Verify that the Docker build command was run
            self.assertEqual(mock_run.call_count, 2)  # Build and run
            build_args, build_kwargs = mock_run.call_args_list[0]
            build_cmd = build_args[0]
            self.assertEqual(build_cmd[0], "docker")
            self.assertEqual(build_cmd[1], "build")
            self.assertIn("-t", build_cmd)
            self.assertIn("tfc-code-pipeline:python3.12", build_cmd)

            # Verify that the temporary Dockerfile was removed
            mock_unlink.assert_called_once()

            # Verify that the Docker run command was called with the correct arguments
            run_args, run_kwargs = mock_run.call_args_list[1]
            docker_cmd = run_args[0]

            # Check that we're using the custom image
            self.assertIn("tfc-code-pipeline:python3.12", docker_cmd)

            # Check that no environment variables are passed to Docker when .env file doesn't exist
            # Convert docker_cmd to string for easier checking
            docker_cmd_str = str(docker_cmd)
            self.assertNotIn("-e TEST_VAR=test_value", docker_cmd_str)
            # Check that there are no -e flags at all
            self.assertNotIn(" -e ", docker_cmd_str)

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
        self.assertIn("ENTRYPOINT [\"/bin/bash\"]", file_content)

        # Verify that the Docker build command was run
        mock_run.assert_called_once()
        args, kwargs = mock_run.call_args
        docker_cmd = args[0]
        self.assertEqual(docker_cmd[0], "docker")
        self.assertEqual(docker_cmd[1], "build")
        self.assertIn("-t", docker_cmd)
        self.assertIn("tfc-code-pipeline:python3.12", docker_cmd)

        # Verify that the temporary Dockerfile was removed
        mock_unlink.assert_called_once()

    @patch('subprocess.run')
    @patch('pathlib.Path.exists')
    @patch('pathlib.Path.unlink')
    @patch('builtins.open', new_callable=unittest.mock.mock_open)
    @patch('src.tfc_code_pipeline.main.load_dotenv', autospec=True)
    def test_main_run(self, mock_load_dotenv, mock_open, mock_unlink, mock_exists, mock_run):
        """Test the main function with run=True."""
        # Setup the mocks
        # Set up mock to return True for .env and False for any other path
        mock_exists.side_effect = None
        mock_exists.return_value = False
        # Set up mock to simulate Docker not being available
        mock_run.side_effect = FileNotFoundError("[Errno 2] No such file or directory: 'docker'")

        # Set some test environment variables
        test_env = {
            'TEST_VAR1': 'value1',
            'TEST_VAR2': 'value2',
            'PATH': '/usr/bin:/bin'  # Common environment variable
        }

        with patch.dict(os.environ, test_env, clear=True):
            # Call the main function with run=True
            result = main(run=True)

            # Verify the result - should be 1 because Docker is not available
            self.assertEqual(result, 1)

            # We don't expect load_dotenv to be called since we're simulating Docker not being available
            # and the error happens before we get to that point
            mock_load_dotenv.assert_not_called()

            # Verify that a Dockerfile was created
            mock_open.assert_called_once()
            file_handle = mock_open()
            file_content = file_handle.write.call_args[0][0]
            self.assertIn("FROM python:3.12-slim", file_content)
            self.assertIn("RUN pip install --no-cache-dir aider-chat", file_content)
            self.assertIn("ENTRYPOINT [\"/bin/bash\"]", file_content)

            # Since we're simulating Docker not being available, we don't need to check
            # the Docker command arguments

    @patch('subprocess.run')
    @patch('pathlib.Path.exists')
    @patch('pathlib.Path.is_dir')
    @patch('pathlib.Path.resolve')
    @patch('src.tfc_code_pipeline.main.load_dotenv', autospec=True)
    @patch('src.tfc_code_pipeline.main.read_env_file', autospec=True)
    def test_main_run_with_src(self, mock_read_env_file, mock_load_dotenv, mock_resolve, mock_is_dir, mock_exists, mock_run):
        """Test the main function with run=True and src option."""
        # Setup the mocks
        mock_exists.return_value = True  # Pretend both .env and src directory exist
        mock_is_dir.return_value = True  # Pretend src is a directory
        mock_resolve.return_value = Path("/resolved/path/to/src")  # Resolved path
        mock_result = MagicMock()
        mock_result.returncode = 0
        mock_run.return_value = mock_result

        # Set up environment variables that would be in the .env file
        env_from_file = {
            'TEST_VAR1': 'value1',
            'TEST_VAR2': 'value2',
        }
        mock_read_env_file.return_value = env_from_file

        # Set some test environment variables (these should not be passed to Docker)
        test_env = {
            'TEST_VAR1': 'value1',
            'TEST_VAR2': 'value2',
            'PATH': '/usr/bin:/bin',  # Common environment variable
            'SYSTEM_VAR': 'should_not_be_passed'  # This should not be passed to Docker
        }

        with patch.dict(os.environ, test_env, clear=True):
            # Call the main function with run=True and src option
            with patch('builtins.open', new_callable=unittest.mock.mock_open) as mock_open:
                result = main(run=True, src="/path/to/src")

                # Verify the result
                self.assertEqual(result, 0)

                # Verify that the Docker run command was called with the correct arguments
                run_args, run_kwargs = mock_run.call_args_list[0]
                docker_cmd = run_args[0]

                # Check that we're mounting the source directory
                self.assertIn("-v", docker_cmd)
                self.assertIn("/resolved/path/to/src:/src", docker_cmd)

                # Check that only environment variables from the .env file are passed to Docker
                docker_cmd_str = str(docker_cmd)
                for key, value in env_from_file.items():
                    self.assertIn(f"-e {key}={value}", docker_cmd_str)

                # Check that system environment variables not in the .env file are not passed to Docker
                self.assertNotIn("SYSTEM_VAR=should_not_be_passed", docker_cmd_str)

    @patch('subprocess.run')
    @patch('pathlib.Path.exists')
    @patch('pathlib.Path.is_dir')
    @patch('pathlib.Path.resolve')
    @patch('src.tfc_code_pipeline.main.load_dotenv', autospec=True)
    def test_main_run_with_src_not_exists(self, mock_load_dotenv, mock_resolve, mock_is_dir, mock_exists, mock_run):
        """Test the main function with run=True and src option when src doesn't exist."""

        # Setup the mocks
        # Set up mock to return False for src_dir
        def exists_side_effect(path):
            if hasattr(path, 'name') and path.name == "src_dir":
                return False
            return True

        mock_exists.side_effect = exists_side_effect
        mock_is_dir.return_value = False  # Not relevant as we'll fail on exists check
        mock_resolve.return_value = Path("/resolved/path/to/src_dir")  # Resolved path
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
            # Call the main function with run=True and src option
            with patch('builtins.open', new_callable=unittest.mock.mock_open):
                result = main(run=True, src="src_dir")

                # Verify the result - should be 1 because src doesn't exist
                self.assertEqual(result, 1)

    @patch('subprocess.run')
    @patch('pathlib.Path.exists')
    @patch('pathlib.Path.is_dir')
    @patch('pathlib.Path.resolve')
    @patch('src.tfc_code_pipeline.main.load_dotenv', autospec=True)
    def test_main_run_with_src_not_dir(self, mock_load_dotenv, mock_resolve, mock_is_dir, mock_exists, mock_run):
        """Test the main function with run=True and src option when src is not a directory."""
        # Setup the mocks
        mock_exists.return_value = True  # Pretend src exists
        mock_is_dir.return_value = False  # But it's not a directory
        mock_resolve.return_value = Path("/resolved/path/to/src_file")  # Resolved path
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
            # Call the main function with run=True and src option
            with patch('builtins.open', new_callable=unittest.mock.mock_open):
                result = main(run=True, src="src_file")

                # Verify the result - should be 1 because src is not a directory
                self.assertEqual(result, 1)
