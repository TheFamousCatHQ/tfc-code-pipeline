# Logging Utilities

This module provides centralized logging configuration for the TFC Code Pipeline. It ensures consistent logging behavior across all components of the codebase.

## Overview

The `logging_utils` module offers a simple way to configure logging for your modules with consistent formatting and behavior. It handles:

- Setting up loggers to output to stderr
- Configuring log formats
- Setting appropriate log levels
- Preventing duplicate log messages
- Providing debug confirmation messages

## Usage

### Simplified Usage (Recommended)

The simplest way to get a configured logger is to use the `get_logger` function, which creates and configures a logger in a single call:

```python
# Get a configured logger for your module
try:
    # Try importing directly (for Docker/installed package)
    from logging_utils import get_logger
except ImportError:
    # Fall back to src-prefixed import (for local development)
    from src.logging_utils import get_logger

# Get a configured logger (automatically uses your module name)
logger = get_logger()

# Now you can use the logger
logger.info("This is an info message")
logger.debug("This is a debug message - only shown when verbose=True")
logger.warning("This is a warning message")
logger.error("This is an error message")
```

### Traditional Usage (Legacy)

For backward compatibility, you can still use the original approach:

```python
import logging
import sys

# Set up module-level logger
logger = logging.getLogger(__name__)

# Configure logging using the centralized function
try:
    # Try importing directly (for Docker/installed package)
    from logging_utils import configure_logging
except ImportError:
    # Fall back to src-prefixed import (for local development)
    from src.logging_utils import configure_logging

# Configure logging for this module
configure_logging(module_name="your_module_name")

# Now you can use the logger
logger.info("This is an info message")
logger.debug("This is a debug message - only shown when verbose=True")
logger.warning("This is a warning message")
logger.error("This is an error message")
```

### Configuration Options

#### get_logger Function

The `get_logger` function accepts the following parameters:

- `module_name` (str, optional): Name of the module requesting the logger. If None, automatically determines the caller's module name.
- `verbose` (bool, default=False): Whether to enable verbose (DEBUG) logging
- `include_module_name` (bool, default=True): Whether to include the module name in the log format

#### configure_logging Function

The `configure_logging` function accepts the following parameters:

- `verbose` (bool, default=False): Whether to enable verbose (DEBUG) logging
- `module_name` (str, optional): Name of the module being configured, used for the confirmation message
- `specific_logger` (logging.Logger, optional): Specific logger to configure instead of the root logger
- `include_module_name` (bool, default=True): Whether to include the module name in the log format

### Examples

#### Using get_logger (Recommended)

##### Basic Usage

```python
# Get a configured logger with automatic module name detection
from logging_utils import get_logger

logger = get_logger()
logger.info("This is an info message")
```

##### Enabling Verbose Logging

```python
# Get a logger with verbose (DEBUG) logging enabled
logger = get_logger(verbose=True)
logger.debug("This debug message will be displayed")
```

##### Configuring a Logger with Simpler Format

```python
# Get a logger with a simpler format (no module name in output)
logger = get_logger(include_module_name=False)
# Output will be: "INFO - Your message" instead of "INFO - module_name - Your message"
```

##### Specifying a Custom Module Name

```python
# Get a logger with a custom module name
logger = get_logger(module_name="custom_module_name")
```

#### Using configure_logging (Legacy)

##### Configuring Logging for a Module

```python
# In your module's main function or at the top level
configure_logging(verbose=args.verbose, module_name="my_module")
```

##### Configuring a Specific Logger with Simpler Format

```python
# Configure a specific logger with a simpler format (no module name in output)
my_logger = logging.getLogger("my_specific_logger")
configure_logging(
    specific_logger=my_logger,
    include_module_name=False,
    module_name="my_module"
)
```

##### Enabling Verbose Logging

```python
# Enable verbose (DEBUG) logging
configure_logging(verbose=True, module_name="my_module")
```

## Best Practices

1. **Use the get_logger function for simplicity**:
   - Prefer `get_logger()` over manual logger setup and configuration
   - This single call handles creation and configuration in one step
   - The function automatically detects your module name

2. **Always use the centralized logging utilities**:
   - Don't create your own logging handlers or formatters
   - Don't call `logging.basicConfig()` directly
   - Don't configure loggers manually with custom handlers

3. **Set up a module-level logger** (if not using `get_logger`):
   ```python
   logger = logging.getLogger(__name__)
   ```

4. **Use appropriate log levels**:
   - DEBUG: Detailed information, typically useful only for diagnosing problems
   - INFO: Confirmation that things are working as expected
   - WARNING: An indication that something unexpected happened, but the program is still working
   - ERROR: Due to a more serious problem, the program has not been able to perform a function
   - CRITICAL: A very serious error, indicating that the program itself may be unable to continue running

4. **Include context in log messages**:
   ```python
   logger.info(f"Processing file: {file_path}")
   ```

5. **Log exceptions properly**:
   ```python
   try:
       # Some code that might raise an exception
       process_file(file_path)
   except Exception as e:
       logger.exception(f"Error processing file {file_path}: {e}")
       # or
       logger.error(f"Error processing file {file_path}: {e}", exc_info=True)
   ```

## Implementation Details

### get_logger Function

The `get_logger` function:

1. Automatically determines the caller's module name if not provided
2. Creates a logger with the appropriate name
3. Configures it using the `configure_logging` function
4. Returns the configured logger ready to use

### configure_logging Function

The `configure_logging` function:

1. Determines which logger to configure (root logger or specific logger)
2. Removes existing handlers to prevent duplicate logs
3. Creates a console handler that writes to stderr
4. Sets the log format based on whether to include the module name
5. Adds the handler to the target logger
6. Sets the log level based on the verbose flag
7. Logs a confirmation message

### Log Formats

The default log format is:
- With module name: `%(levelname)s - %(name)s - %(message)s`
- Without module name: `%(levelname)s - %(message)s`
