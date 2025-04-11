# Code Processor Framework

This framework provides a common base class for processing code files using Aider.

## Overview

The `code_processor` module provides a base class (`CodeProcessor`) that can be extended to create specialized code processors for different tasks, such as:

- Explaining code
- Writing unit tests
- Refactoring code
- Documenting code

Each processor only needs to define its specific message and description, while the common functionality (finding files, processing them with Aider, etc.) is handled by the base class.

## Available Processors

### ExplainCodeProcessor

- **Script**: `explain-code`
- **Purpose**: Explains code in source files
- **Default Message**: "explain this code"

### WriteTestsProcessor

- **Script**: `write-tests`
- **Purpose**: Writes unit tests for source files without using mocks
- **Default Message**: "write unit tests without using mocks for all functions found in this file. If tests already exist, check if they are up to date, if not update them to cover the current functionality."

### TokenUtilsTestProcessor

- **Script**: `write-token-utils-tests`
- **Purpose**: Specialized processor for writing tests for tokenUtils.js
- **Default Message**: "write unit tests without using mocks for all functions found in tokenUtils.js. If tests already exists, check if their are up to date, if not update them to cover the current functionality."

## Creating a New Processor

To create a new processor:

1. Create a new module in `src/`
2. Define a class that inherits from `CodeProcessor`
3. Implement the required methods:
   - `get_default_message()`
   - `get_description()`
4. Optionally override other methods for specialized behavior
5. Add the module to `pyproject.toml`

Example:

```python
from code_processor import CodeProcessor

class MyCustomProcessor(CodeProcessor):
    def get_default_message(self) -> str:
        return "my custom message for aider"

    def get_description(self) -> str:
        return "My custom code processor"

def main() -> int:
    processor = MyCustomProcessor()
    return processor.run()

if __name__ == "__main__":
    import sys
    sys.exit(main())
```

## Usage

Each processor can be used with the following arguments:

- `--directory`: Directory to search for source files (required)
- `--file`: Specific file to process (optional, overrides directory search)
- `--message`: Custom message to pass to aider (optional, defaults to the processor's default message)

Example:

```bash
# Explain code in a directory
explain-code --directory /path/to/source

# Write tests for a specific file with a custom message
write-tests --file /path/to/file.js --message "write comprehensive unit tests for this file"

# Write tests for tokenUtils.js
write-token-utils-tests --directory /path/to/project
```
