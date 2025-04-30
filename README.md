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

### FindBugsProcessor

- **Script**: `find-bugs`
- **Purpose**: Finds potential bugs in source files and outputs results as JSON
- **Default Message**: "analyze this code and identify potential bugs, issues, or vulnerabilities. For each issue found, provide: 1) a brief description, 2) the line number(s), 3) severity (high/medium/low), 4) confidence level (high/medium/low), and 5) a suggested fix."
- **Output**: Generates a `bugs_report.json` file in the specified directory

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

## Installation

This project uses Poetry for dependency management. To install and use the commands:

1. Clone the repository:
   ```bash
   git clone <repository-url>
   cd tfc-code-pipeline
   ```

2. Install the package using Poetry:
   ```bash
   poetry install
   ```

3. Activate the Poetry virtual environment:
   ```bash
   poetry shell
   ```

After installation, all commands will be available in your PATH when the Poetry environment is active.

## Poetry Scripts

This project provides several Poetry scripts that can be used to process code files. All scripts are available after installation when the Poetry environment is active.

### find-source-files

Finds source files in a directory, excluding dependencies, tests, and other non-core files.

**Usage:**
```bash
find-source-files --directory /path/to/source
```

**Options:**
- `--directory`: Directory to search for source files (required)

**Example:**
```bash
# Find source files in a directory
find-source-files --directory /path/to/project
```

### explain-code

Explains code in source files using aider. This script finds source files in a specified directory and then calls aider for each file with the message "explain this code".

**Usage:**
```bash
explain-code --directory /path/to/source [--file /path/to/specific/file.js] [--message "custom message"]
```

**Options:**
- `--directory`: Directory to search for source files (required)
- `--file`: Specific file to process (optional, overrides directory search)
- `--message`: Custom message to pass to aider (optional, defaults to "explain this code")

**Example:**
```bash
# Explain code in a directory
explain-code --directory /path/to/source

# Explain a specific file with a custom message
explain-code --file /path/to/file.js --message "explain this code in detail"
```

### write-tests

Writes unit tests for source files using aider. This script finds source files in a specified directory and then calls aider for each file with a message to write unit tests without using mocks.

**Usage:**
```bash
write-tests --directory /path/to/source [--file /path/to/specific/file.js] [--message "custom message"]
```

**Options:**
- `--directory`: Directory to search for source files (required)
- `--file`: Specific file to process (optional, overrides directory search)
- `--message`: Custom message to pass to aider (optional, defaults to "write unit tests without using mocks for all functions found in this file. If tests already exist, check if they are up to date, if not update them to cover the current functionality.")

**Example:**
```bash
# Write tests for all source files in a directory
write-tests --directory /path/to/source

# Write tests for a specific file with a custom message
write-tests --file /path/to/file.js --message "write comprehensive unit tests for this file"
```

### tfc-code-pipeline

A Docker-based wrapper for the other scripts. It creates a Docker container based on Python 3.12, installs Aider and the package itself in the container, and runs the specified command with the provided messages.

**Usage:**
```bash
tfc-code-pipeline [--build-only] [--run] [--src /path/to/source] [--messages "custom message"] [--cmd explain_code|write_tests]
```

**Options:**
- `--build-only`: Only build the Docker image without running the container
- `--run`: Run the Docker container with the provided messages
- `--src`: Directory to mount in the Docker container under /src
- `--messages`: Custom message to pass to aider (default: "Hello")
- `--cmd`: Command to run in the Docker container (choices: "explain_code" or "write_tests", default: "explain_code")

**Example:**
```bash
# Build the Docker image only
tfc-code-pipeline --build-only

# Run explain-code in a Docker container
tfc-code-pipeline --run --src /path/to/source --messages "explain this code" --cmd explain_code

# Run write-tests in a Docker container
tfc-code-pipeline --run --src /path/to/source --cmd write_tests
```

## Running Scripts

You can run the scripts in two ways:

1. **Activate the Poetry environment first:**
   ```bash
   poetry shell
   explain-code --directory /path/to/source
   ```

2. **Run without activating the environment:**
   ```bash
   poetry run explain-code --directory /path/to/source
   ```
