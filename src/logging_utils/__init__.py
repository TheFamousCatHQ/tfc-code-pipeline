"""
Logging configuration and utility functions for the Usual Suspects application.
Provides a centralized logging setup with YAML configuration and convenience methods.
"""

import logging
import logging.config
import os
from typing import Any

import yaml

# Setup paths
script_dir = os.path.dirname(os.path.abspath(__file__))
parent_dir = os.path.dirname(script_dir)
logging_config_path = os.path.join(parent_dir, 'logging.yaml')

isInitialized = False


def init_logging() -> None:
    """Initialize logging configuration from YAML file."""
    global isInitialized
    if isInitialized:
        return
    isInitialized = True
    try:
        with open(logging_config_path, 'rt') as f:
            config = yaml.safe_load(f.read())
        logging.config.dictConfig(config)
        logging.info("Initialized logging")
    except Exception as e:
        # Fallback to basic configuration if YAML loading fails
        logging.basicConfig(
            level=logging.INFO,
            format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
        )
        logging.error(f"Failed to load logging config from {logging_config_path}: {e}")


def get_logger(name: str = "tfc-code-pipeline") -> logging.Logger:
    """
    Get a logger instance with the specified name.

    Args:
        name: Logger name, defaults to "usual-suspects"

    Returns:
        logging.Logger: Configured logger instance
    """
    return logging.getLogger(name)


def log_info(*args: Any) -> None:
    """Log an INFO level message."""
    get_logger().info(*args)


def log_debug(*args: Any) -> None:
    """Log a DEBUG level message."""
    get_logger().debug(*args)


def log_warn(*args: Any) -> None:
    """Log a WARNING level message."""
    get_logger().warning(*args)


def log_error(*args: Any, **kwargs: Any) -> None:
    """
    Log an ERROR level message.

    Args:
        *args: Message and arguments to log
        **kwargs: Additional logging parameters (e.g., exc_info, stack_info)
    """
    get_logger().error(*args, **kwargs)


def log_exception(*args: Any, **kwargs: Any) -> None:
    """
    Log an exception with traceback at ERROR level.

    Args:
        *args: Message and arguments to log
        **kwargs: Additional logging parameters (e.g., exc_info, stack_info)
    """
    get_logger().exception(*args, **kwargs)


# Initialize logging when module is imported
init_logging()
