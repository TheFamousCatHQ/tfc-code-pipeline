"""Tests for the CLI module.

This module contains tests for the command-line interface of the TFC Test Writer Aider.
"""

import unittest
from unittest.mock import patch, MagicMock
from argparse import Namespace

# Local application imports
from tfc_test_writer_aider.cli import parse_args, cli


class TestCli(unittest.TestCase):
    """Tests for the CLI functions."""

    def test_parse_args_default(self):
        """Test parse_args with default arguments."""
        with patch('argparse.ArgumentParser.parse_args') as mock_parse_args:
            mock_parse_args.return_value = Namespace(build_only=False, run=False, messages="Hello", src=None)
            args = parse_args([])
            self.assertFalse(args.build_only)
            self.assertFalse(args.run)
            self.assertEqual(args.messages, "Hello")
            self.assertIsNone(args.src)

    def test_parse_args_build_only(self):
        """Test parse_args with --build-only flag."""
        with patch('argparse.ArgumentParser.parse_args') as mock_parse_args:
            mock_parse_args.return_value = Namespace(build_only=True, run=False, messages="Hello", src=None)
            args = parse_args(['--build-only'])
            self.assertTrue(args.build_only)
            self.assertFalse(args.run)
            self.assertEqual(args.messages, "Hello")
            self.assertIsNone(args.src)

    def test_parse_args_run(self):
        """Test parse_args with --run flag."""
        with patch('argparse.ArgumentParser.parse_args') as mock_parse_args:
            mock_parse_args.return_value = Namespace(build_only=False, run=True, messages="Hello", src=None)
            args = parse_args(['--run'])
            self.assertFalse(args.build_only)
            self.assertTrue(args.run)
            self.assertEqual(args.messages, "Hello")
            self.assertIsNone(args.src)

    def test_parse_args_messages(self):
        """Test parse_args with --messages option."""
        with patch('argparse.ArgumentParser.parse_args') as mock_parse_args:
            mock_parse_args.return_value = Namespace(build_only=False, run=True, messages="Custom message", src=None)
            args = parse_args(['--run', '--messages', 'Custom message'])
            self.assertFalse(args.build_only)
            self.assertTrue(args.run)
            self.assertEqual(args.messages, "Custom message")
            self.assertIsNone(args.src)

    def test_parse_args_src(self):
        """Test parse_args with --src option."""
        with patch('argparse.ArgumentParser.parse_args') as mock_parse_args:
            mock_parse_args.return_value = Namespace(build_only=False, run=True, messages="Hello", src="/path/to/src")
            args = parse_args(['--run', '--src', '/path/to/src'])
            self.assertFalse(args.build_only)
            self.assertTrue(args.run)
            self.assertEqual(args.messages, "Hello")
            self.assertEqual(args.src, "/path/to/src")

    @patch('tfc_test_writer_aider.cli.parse_args')
    @patch('tfc_test_writer_aider.cli.main')
    def test_cli(self, mock_main, mock_parse_args):
        """Test the cli function."""
        # Setup mocks
        mock_parse_args.return_value = Namespace(build_only=False, run=False, messages="Hello", src=None)
        mock_main.return_value = 0

        # Call the cli function
        result = cli()

        # Verify the result
        self.assertEqual(result, 0)
        mock_parse_args.assert_called_once()
        mock_main.assert_called_once_with(build_only=False, run=False, messages="Hello", src=None)

    @patch('tfc_test_writer_aider.cli.parse_args')
    @patch('tfc_test_writer_aider.cli.main')
    def test_cli_build_only(self, mock_main, mock_parse_args):
        """Test the cli function with build_only=True."""
        # Setup mocks
        mock_parse_args.return_value = Namespace(build_only=True, run=False, messages="Hello", src=None)
        mock_main.return_value = 0

        # Call the cli function
        result = cli()

        # Verify the result
        self.assertEqual(result, 0)
        mock_parse_args.assert_called_once()
        mock_main.assert_called_once_with(build_only=True, run=False, messages="Hello", src=None)

    @patch('tfc_test_writer_aider.cli.parse_args')
    @patch('tfc_test_writer_aider.cli.main')
    def test_cli_run(self, mock_main, mock_parse_args):
        """Test the cli function with run=True."""
        # Setup mocks
        mock_parse_args.return_value = Namespace(build_only=False, run=True, messages="Hello", src=None)
        mock_main.return_value = 0

        # Call the cli function
        result = cli()

        # Verify the result
        self.assertEqual(result, 0)
        mock_parse_args.assert_called_once()
        mock_main.assert_called_once_with(build_only=False, run=True, messages="Hello", src=None)

    @patch('tfc_test_writer_aider.cli.parse_args')
    @patch('tfc_test_writer_aider.cli.main')
    def test_cli_run_with_messages(self, mock_main, mock_parse_args):
        """Test the cli function with run=True and custom messages."""
        # Setup mocks
        mock_parse_args.return_value = Namespace(build_only=False, run=True, messages="Custom message", src=None)
        mock_main.return_value = 0

        # Call the cli function
        result = cli()

        # Verify the result
        self.assertEqual(result, 0)
        mock_parse_args.assert_called_once()
        mock_main.assert_called_once_with(build_only=False, run=True, messages="Custom message", src=None)

    @patch('tfc_test_writer_aider.cli.parse_args')
    @patch('tfc_test_writer_aider.cli.main')
    def test_cli_run_with_src(self, mock_main, mock_parse_args):
        """Test the cli function with run=True and src option."""
        # Setup mocks
        mock_parse_args.return_value = Namespace(build_only=False, run=True, messages="Hello", src="/path/to/src")
        mock_main.return_value = 0

        # Call the cli function
        result = cli()

        # Verify the result
        self.assertEqual(result, 0)
        mock_parse_args.assert_called_once()
        mock_main.assert_called_once_with(build_only=False, run=True, messages="Hello", src="/path/to/src")
