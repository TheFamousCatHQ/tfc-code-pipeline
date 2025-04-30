# Code Processor Framework

This framework provides a common base class for processing code files using Aider.

## Overview

The `code_processor` module provides a base class (`CodeProcessor`) that can be extended to create specialized code processors for different tasks, such as:

- Explaining code
- Writing unit tests
- Finding bugs
- Analyzing code complexity
- Refactoring code
- Documenting code

Each processor only needs to define its specific message and description, while the common functionality (finding files, processing them with Aider, etc.) is handled by the base class.

## How Code Processors Work

1. **Source File Discovery**: The processor finds source files in the specified directory using the `find-source-files` tool, which excludes dependencies, tests, and other non-core files.

2. **Aider Integration**: For each source file, the processor calls Aider with a specific prompt (the default message or a custom one provided by the user).

3. **Processing Output**:
   - Basic processors (like `ExplainCodeProcessor`) simply display Aider's output
   - Advanced processors (like `FindBugsProcessor`) parse Aider's output to generate structured data or reports

4. **Reporting**: All processors report which files were processed and any errors encountered.

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
- **Default Message**: "Analyze this code and identify potential bugs. I am not interested in general suggestions for improvements just hard, plain bugs like off-by-one-errors. For each issue found, provide: 1) a brief description, 2) the line number(s), 3) severity (high/medium/low), 4) confidence level (high/medium/low), and 5) a suggested fix. Your output will be an artifact name FILENAME-bugreport.json"
- **Output**: Generates a `bugs_report.json` file in the specified directory

### ComplexityAnalyzerProcessor

- **Script**: `analyze-complexity`
- **Purpose**: Analyzes code complexity using an LLM via `aider` to identify complex/hard-to-understand code sections and suggest improvements.
- **Default Message**: "Analyze this code to identify the most complex and difficult-to-understand parts. For each complex section you identify, please explain: 1. Why it is considered complex (e.g., high cognitive load, complex logic, deep nesting, unclear naming, potential for bugs). 2. The specific line numbers or range of lines for the complex code. 3. Suggestions for simplifying or improving the readability of this section. Focus on areas that would be challenging for a new developer to grasp quickly."
- **Output**: LLM analysis printed to standard output (via `aider`).

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

### analyze-complexity

Analyzes code complexity in source files using an LLM via the `aider` tool. This script finds source files in a specified directory and prompts `aider` to identify complex/hard-to-understand sections and suggest improvements.

**Usage:**
```bash
analyze-complexity --directory /path/to/source [--file /path/to/specific/file.py] [--message "custom analysis prompt"]
```

**Options:**
- `--directory`: Directory to search for source files (required)
- `--file`: Specific file to process (optional, overrides directory search)
- `--message`: Custom message/prompt to pass to aider (optional, overrides the default complexity analysis prompt)

**Example:**
```bash
# Analyze complexity for all source files in a directory
analyze-complexity --directory /path/to/source

# Analyze complexity for a specific file
analyze-complexity --file /path/to/file.py
```

### tfc-code-pipeline

A Docker-based wrapper for the other scripts. It creates a Docker container based on Python 3.12, installs Aider and the package itself in the container, and runs the specified command with the provided messages.

**Usage:**
```bash
tfc-code-pipeline [--build-only] [--run] [--src /path/to/source] [--messages "custom message"] [--cmd explain_code|write_tests|find_bugs|analyze_complexity]
```

**Options:**
- `--build-only`: Only build the Docker image without running the container
- `--run`: Run the Docker container with the provided messages
- `--src`: Directory to mount in the Docker container under /src
- `--messages`: Custom message to pass to aider (default: "Hello")
- `--cmd`: Command to run in the Docker container (choices: "explain_code", "write_tests", "find_bugs", or "analyze_complexity", default: "explain_code")

**Example:**
```bash
# Build the Docker image only
tfc-code-pipeline --build-only

# Run explain-code in a Docker container
tfc-code-pipeline --run --src /path/to/source --messages "explain this code" --cmd explain_code

# Run write-tests in a Docker container
tfc-code-pipeline --run --src /path/to/source --cmd write_tests

# Run find-bugs in a Docker container
tfc-code-pipeline --run --src /path/to/source --cmd find_bugs

# Run analyze-complexity in a Docker container
tfc-code-pipeline --run --src /path/to/source --cmd analyze_complexity
```

## Environment Variables

This project supports loading environment variables from a `.env` file. When using the Docker-based approach (`tfc-code-pipeline`), these variables are automatically passed to the Docker container.

Common environment variables:
- `OPENAI_API_KEY`: API key for OpenAI (used by Aider)
- `DEBUG`: Enable debug mode (set to "True" to enable)

To use environment variables, create a `.env` file in the project root directory:

```
OPENAI_API_KEY=your-api-key-here
DEBUG=False
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

## Integration with Development Workflows

Code processors can be integrated into development workflows in several ways:

1. **Local Development**: Developers can run processors on their local machines to explain code, write tests, or find bugs.

2. **CI/CD Pipelines**: Processors can be integrated into CI/CD pipelines to automatically analyze code, find bugs, or generate tests.

3. **Code Review**: Processors can be used during code review to identify potential issues or suggest improvements.

4. **Documentation**: Processors can be used to generate documentation or explanations for code.
