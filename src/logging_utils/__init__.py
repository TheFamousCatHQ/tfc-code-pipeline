#!/usr/bin/env python3
"""
Utility module for configuring logging across the codebase.

This module provides a centralized way to configure logging for all components
of the TFC Code Pipeline, ensuring consistent logging behavior.
"""

import logging
import sys
import inspect
from typing import Optional

# Set up module-level logger
logger = logging.getLogger(__name__)


def get_logger(
    module_name: Optional[str] = None,
    verbose: bool = False,
    include_module_name: bool = True
) -> logging.Logger:
    """Get a configured logger instance in a single call.

    This function creates and configures a logger with consistent settings,
    returning it ready to use. It's the recommended way to get a logger
    in the TFC Code Pipeline.

    Args:
        module_name: Name of the module requesting the logger. If None,
                    attempts to determine the caller's module name.
        verbose: Whether to enable verbose (DEBUG) logging.
        include_module_name: Whether to include the module name in the log format.
                            Set to False for simpler output format.

    Returns:
        A configured logger instance ready to use.

    Example:
        ```python
        # Get a configured logger for your module
        from logging_utils import get_logger

        logger = get_logger()  # Automatically uses your module name
        logger.info("This is an info message")
        ```
    """
    # If module_name is not provided, try to determine it from the caller's frame
    if module_name is None:
        # Get the caller's frame (2 levels up: caller -> get_logger)
        frame = inspect.currentframe()
        if frame:
            try:
                frame = frame.f_back
                if frame and frame.f_globals.get('__name__'):
                    module_name = frame.f_globals['__name__']
            finally:
                # Always delete the frame reference to avoid reference cycles
                del frame

    # Create the logger
    new_logger = logging.getLogger(module_name)

    # Configure it
    configure_logging(
        verbose=verbose,
        module_name=module_name,
        specific_logger=new_logger,
        include_module_name=include_module_name
    )

    return new_logger


def configure_logging(verbose: bool = False, module_name: Optional[str] = None, 
                     specific_logger: Optional[logging.Logger] = None,
                     include_module_name: bool = True):
    """Configure logging for the application.

    This function sets up consistent logging across all modules in the codebase.
    It configures the root logger (or a specific logger if provided) to output 
    to stderr with a consistent format, and sets the appropriate log level based 
    on the verbose flag.

    Args:
        verbose: Whether to enable verbose (DEBUG) logging.
        module_name: Optional name of the module being configured, used for the
                    confirmation message. If None, a generic message is used.
        specific_logger: Optional specific logger to configure instead of the root logger.
        include_module_name: Whether to include the module name in the log format.
                            Set to False for simpler output format.
    """
    # Determine which logger to configure
    target_logger = specific_logger if specific_logger else logging.getLogger()

    # Remove existing handlers to prevent duplicate logs
    for handler in target_logger.handlers[:]:
        target_logger.removeHandler(handler)

    # Create console handler with stderr
    console = logging.StreamHandler(sys.stderr)

    # Set format based on whether to include module name
    if include_module_name:
        formatter = logging.Formatter('%(levelname)s - %(name)s - %(message)s')
    else:
        formatter = logging.Formatter('%(levelname)s - %(message)s')

    console.setFormatter(formatter)

    # Add handler to target logger
    target_logger.addHandler(console)

    # Set level based on verbose flag
    if verbose:
        target_logger.setLevel(logging.DEBUG)
        log_level_name = "DEBUG"
    else:
        target_logger.setLevel(logging.INFO)
        log_level_name = "INFO"

    # Log confirmation message
    if module_name:
        logger.debug(f"Logging configured for {module_name} at level: {log_level_name}")
    else:
        logger.debug(f"Logging configured at level: {log_level_name}")
