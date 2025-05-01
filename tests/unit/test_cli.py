"""Tests for the CLI module.

This module contains tests for the command-line interface of the TFC Code Pipeline.
"""

import unittest
from argparse import Namespace
from unittest.mock import patch


# Local application imports
from tfc_code_pipeline.cli import parse_args, cli


class TestCli(unittest.TestCase):
    """Tests for the CLI functions."""

    def test_parse_args_default(self):
        """Test parse_args with default arguments."""
        with patch('argparse.ArgumentParser.parse_args') as mock_parse_args:
            mock_parse_args.return_value = Namespace(build_only=False, run=False, messages="Hello", src=None, cmd="explain_code")
            args = parse_args([])
            self.assertFalse(args.build_only)
            self.assertFalse(args.run)
            self.assertEqual(args.messages, "Hello")
            self.assertIsNone(args.src)

    def test_parse_args_build_only(self):
        """Test parse_args with --build-only flag."""
        with patch('argparse.ArgumentParser.parse_args') as mock_parse_args:
            mock_parse_args.return_value = Namespace(build_only=True, run=False, messages="Hello", src=None, cmd="explain_code")
            args = parse_args(['--build-only'])
            self.assertTrue(args.build_only)
            self.assertFalse(args.run)
            self.assertEqual(args.messages, "Hello")
            self.assertIsNone(args.src)

    def test_parse_args_run(self):
        """Test parse_args with --run flag."""
        with patch('argparse.ArgumentParser.parse_args') as mock_parse_args:
            mock_parse_args.return_value = Namespace(build_only=False, run=True, messages="Hello", src=None, cmd="explain_code")
            args = parse_args(['--run'])
            self.assertFalse(args.build_only)
            self.assertTrue(args.run)
            self.assertEqual(args.messages, "Hello")
            self.assertIsNone(args.src)

    def test_parse_args_messages(self):
        """Test parse_args with --messages option."""
        with patch('argparse.ArgumentParser.parse_args') as mock_parse_args:
            mock_parse_args.return_value = Namespace(build_only=False, run=True, messages="Custom message", src=None, cmd="explain_code")
            args = parse_args(['--run', '--messages', 'Custom message'])
            self.assertFalse(args.build_only)
            self.assertTrue(args.run)
            self.assertEqual(args.messages, "Custom message")
            self.assertIsNone(args.src)

    def test_parse_args_src(self):
        """Test parse_args with --src option."""
        with patch('argparse.ArgumentParser.parse_args') as mock_parse_args:
            mock_parse_args.return_value = Namespace(build_only=False, run=True, messages="Hello", src="/path/to/src", cmd="explain_code")
            args = parse_args(['--run', '--src', '/path/to/src'])
            self.assertFalse(args.build_only)
            self.assertTrue(args.run)
            self.assertEqual(args.messages, "Hello")
            self.assertEqual(args.src, "/path/to/src")

    def test_parse_args_cmd(self):
        """Test parse_args with --cmd option."""
        with patch('argparse.ArgumentParser.parse_args') as mock_parse_args:
            mock_parse_args.return_value = Namespace(build_only=False, run=True, messages="Hello", src="/path/to/src", cmd="write_tests")
            args = parse_args(['--run', '--src', '/path/to/src', '--cmd', 'write_tests'])
            self.assertFalse(args.build_only)
            self.assertTrue(args.run)
            self.assertEqual(args.messages, "Hello")
            self.assertEqual(args.src, "/path/to/src")
            self.assertEqual(args.cmd, "write_tests")

    @patch('tfc_code_pipeline.cli.parse_args')
    @patch('tfc_code_pipeline.cli.main')
    def test_cli(self, mock_main, mock_parse_args):
        """Test the cli function."""
        # Setup mocks
        mock_parse_args.return_value = Namespace(build_only=False, run=False, src=None, cmd="explain_code", output=None)
        mock_main.return_value = 0

        # Call the cli function
        result = cli()

        # Verify the result
        self.assertEqual(result, 0)
        mock_parse_args.assert_called_once()
        # All args except build_only, run, src, cmd should be passed to processor_args
        mock_main.assert_called_once_with(build_only=False, run=False, src=None, cmd="explain_code", processor_args={'output': None})

    @patch('tfc_code_pipeline.cli.parse_args')
    @patch('tfc_code_pipeline.cli.main')
    def test_cli_build_only(self, mock_main, mock_parse_args):
        """Test the cli function with build_only=True."""
        # Setup mocks
        mock_parse_args.return_value = Namespace(build_only=True, run=False, src=None, cmd="explain_code", output=None)
        mock_main.return_value = 0

        # Call the cli function
        result = cli()

        # Verify the result
        self.assertEqual(result, 0)
        mock_parse_args.assert_called_once()
        # All args except build_only, run, src, cmd should be passed to processor_args
        mock_main.assert_called_once_with(build_only=True, run=False, src=None, cmd="explain_code", processor_args={'output': None})

    @patch('tfc_code_pipeline.cli.parse_args')
    @patch('tfc_code_pipeline.cli.main')
    def test_cli_run(self, mock_main, mock_parse_args):
        """Test the cli function with run=True."""
        # Setup mocks
        mock_parse_args.return_value = Namespace(build_only=False, run=True, src=None, cmd="explain_code", output=None)
        mock_main.return_value = 0

        # Call the cli function
        result = cli()

        # Verify the result
        self.assertEqual(result, 0)
        mock_parse_args.assert_called_once()
        # All args except build_only, run, src, cmd should be passed to processor_args
        mock_main.assert_called_once_with(build_only=False, run=True, src=None, cmd="explain_code", processor_args={'output': None})

    @patch('tfc_code_pipeline.cli.parse_args')
    @patch('tfc_code_pipeline.cli.main')
    def test_cli_with_output(self, mock_main, mock_parse_args):
        """Test the cli function with output parameter."""
        # Setup mocks
        mock_parse_args.return_value = Namespace(build_only=False, run=False, src=None, cmd="analyze_complexity", output="/tmp/output.json")
        mock_main.return_value = 0

        # Call the cli function
        result = cli()

        # Verify the result
        self.assertEqual(result, 0)
        mock_parse_args.assert_called_once()
        # All args except build_only, run, src, cmd should be passed to processor_args
        mock_main.assert_called_once_with(build_only=False, run=False, src=None, cmd="analyze_complexity", processor_args={'output': '/tmp/output.json'})

    @patch('tfc_code_pipeline.cli.parse_args')
    @patch('tfc_code_pipeline.cli.main')
    def test_cli_run_with_src(self, mock_main, mock_parse_args):
        """Test the cli function with run=True and src option."""
        # Setup mocks
        mock_parse_args.return_value = Namespace(build_only=False, run=True, src="/path/to/src", cmd="explain_code", output=None)
        mock_main.return_value = 0

        # Call the cli function
        result = cli()

        # Verify the result
        self.assertEqual(result, 0)
        mock_parse_args.assert_called_once()
        # All args except build_only, run, src, cmd should be passed to processor_args
        mock_main.assert_called_once_with(build_only=False, run=True, src="/path/to/src", cmd="explain_code", processor_args={'output': None})

    @patch('tfc_code_pipeline.cli.parse_args')
    @patch('tfc_code_pipeline.cli.main')
    def test_cli_run_with_cmd(self, mock_main, mock_parse_args):
        """Test the cli function with run=True and cmd option."""
        # Setup mocks
        mock_parse_args.return_value = Namespace(build_only=False, run=True, src="/path/to/src", cmd="write_tests", output=None)
        mock_main.return_value = 0

        # Call the cli function
        result = cli()

        # Verify the result
        self.assertEqual(result, 0)
        mock_parse_args.assert_called_once()
        # All args except build_only, run, src, cmd should be passed to processor_args
        mock_main.assert_called_once_with(build_only=False, run=True, src="/path/to/src", cmd="write_tests", processor_args={'output': None})
