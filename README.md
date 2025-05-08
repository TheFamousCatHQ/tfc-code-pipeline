# Code Processor Framework

This framework provides a common base class for processing code files using Aider.

## Sonar Analyzer

The `sonar-analyze` tool analyzes Sonar scanner reports and generates improvement suggestions for each component/file, including prompts suitable for AI Coding Agents. It processes both issues and file complexity measures.

### Usage

```bash
poetry run sonar-analyze --report-file path/to/sonar/report.json [--min-severity SEVERITY] [--output-file path/to/output.json]
```

### Options

- `--report-file`: Path to the Sonar scanner report JSON file (required)
- `--min-severity`: Minimum severity level to include in the analysis (default: MEDIUM)
  - Available options: LOW, INFO, MEDIUM, HIGH, BLOCKER
- `--output-file`: Path to the output file for the analysis results (default: stdout)

### Example

```bash
poetry run sonar-analyze --report-file doc/SONAR_REPORT.json --min-severity HIGH --output-file sonar_suggestions.json
```

This will analyze the Sonar scanner report, filter out issues below the HIGH severity level, identify overly complex files, and write the suggestions to sonar_suggestions.json.

### Features

The tool provides two types of analysis:

1. **Issue Analysis**: Identifies and categorizes issues reported by Sonar scanner based on severity level.

2. **Complexity Analysis**: Identifies overly complex files based on the following metrics:
   - Cyclomatic complexity (threshold: 30)
   - Cognitive complexity (threshold: 25)
   - Lines of code (threshold: 500)
   - Complexity per function (threshold: 5)

For each component/file, the tool generates:
- A summary of issues and/or complexity problems
- Suggestions for improvement
- A detailed prompt for an AI Coding Agent to fix the issues and/or refactor complex code

## Overview

The `code_processor` module provides a base class (`CodeProcessor`) that can be extended to create specialized code
processors for different tasks, such as:

- Explaining code
- Writing unit tests
- Finding bugs
- Analyzing code complexity
- Refactoring code
- Documenting code

Each processor only needs to define its specific message and description, while the common functionality (finding files,
processing them with Aider, etc.) is handled by the base class.

## How Code Processors Work

1. **Source File Discovery**: The processor finds source files in the specified directory using the `find-source-files`
   tool, which excludes dependencies, tests, and other non-core files.

2. **File Processing Strategy**:
    - If `operates_on_whole_codebase` is `False` (default): Each file is processed individually
    - If `operates_on_whole_codebase` is `True`: Files are grouped by parent directory and processed in chunks of up to
      20 files

3. **Aider Integration**: The processor calls Aider with a specific prompt (the default message or a custom one provided
   by the user) and the file(s) to process.

4. **Processing Output**:
    - Basic processors (like `ExplainCodeProcessor`) simply display Aider's output
    - Advanced processors (like `FindBugsProcessor`) parse Aider's output to generate structured data or reports

5. **Reporting**: All processors report which files were processed and any errors encountered.

## Available Processors

### ExplainCodeProcessor

- **Script**: `explain-code`
- **Purpose**: Explains code in source files
- **Default Message**: "explain this code"

### WriteTestsProcessor

- **Script**: `write-tests`
- **Purpose**: Writes unit tests for source files without using mocks
- **Default Message**: "write unit tests without using mocks for all functions found in this file. If tests already
  exist, check if they are up to date, if not update them to cover the current functionality."

### FindBugsProcessor

- **Script**: `find-bugs`
- **Purpose**: Finds potential bugs in source files and outputs results as JSON
- **Default Message**: "Analyze this code and identify potential bugs. I am not interested in general suggestions for
  improvements just hard, plain bugs like off-by-one-errors. For each issue found, provide: 1) a brief description, 2)
  the line number(s), 3) severity (high/medium/low), 4) confidence level (high/medium/low), and 5) a suggested fix. Your
  output will be an artifact name FILENAME-bugreport.json"
- **Output**: Generates a `bugs_report.json` file in the specified directory

### ComplexityAnalyzerProcessor

- **Script**: `analyze-complexity`
- **Purpose**: Analyzes code complexity using an LLM via `aider` to identify complex/hard-to-understand code sections
  and suggest improvements.
- **Default Message**: "Analyze this code to identify the most complex and difficult-to-understand parts. For each
  complex section you identify, please explain: 1. Why it is considered complex (e.g., high cognitive load, complex
  logic, deep nesting, unclear naming, potential for bugs). 2. The specific line numbers or range of lines for the
  complex code. 3. Suggestions for simplifying or improving the readability of this section. Focus on areas that would
  be challenging for a new developer to grasp quickly."
- **Output**: LLM analysis printed to standard output (via `aider`).

## Processor Configuration

### operates_on_whole_codebase

Each processor can be configured to operate on the whole codebase at once or on a file-by-file basis using the
`operates_on_whole_codebase` property:

```python
class MyProcessor(CodeProcessor):
    operates_on_whole_codebase = True  # Process multiple files at once
    # ...
```

When `operates_on_whole_codebase` is `True`:

- Files are grouped by parent directory
- Each chunk contains between 10 and 20 files (when possible)
- The algorithm optimizes for:
    - Keeping files from the same directory together when possible
    - Ensuring chunks have at least 10 files (minimum size)
    - Ensuring no chunk exceeds 20 files (maximum size)
    - Combining small directories that have fewer than 10 files
- Each chunk is processed separately with Aider
- Detailed logging shows how many chunks were created and how files are distributed

This is useful for processors that need to analyze relationships between files or make changes that span multiple files.

## Creating a New Processor

To create a new processor:

1. Create a new module in `src/`
2. Define a class that inherits from `CodeProcessor`
3. Implement the required methods:
    - `get_default_message()`
    - `get_description()`
4. Optionally set configuration properties like `operates_on_whole_codebase`
5. Optionally override other methods for specialized behavior
6. Add the module to `pyproject.toml`

Example:

```python
from code_processor import CodeProcessor


class MyCustomProcessor(CodeProcessor):
    # Set to True if this processor should operate on multiple files at once
    operates_on_whole_codebase = True

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

This project provides several Poetry scripts that can be used to process code files. All scripts are available after
installation when the Poetry environment is active.

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

Explains code in source files using aider. This script finds source files in a specified directory and then calls aider
for each file with the message "explain this code".

**Usage:**

```bash
explain-code --directory /path/to/source [--file /path/to/specific/file.js] [--message "custom message"]
```

**Options:** See [Common Options for All Processors](#common-options-for-all-processors)

**Example:**

```bash
# Explain code in a directory
explain-code --directory /path/to/source

# Explain a specific file with a custom message
explain-code --file /path/to/file.js --message "explain this code in detail"

# Show how files would be chunked without processing them
explain-code --directory /path/to/source --show-only-repo-files-chunks
```

### write-tests

Writes unit tests for source files using aider. This script finds source files in a specified directory and then calls
aider for each file with a message to write unit tests without using mocks.

**Usage:**

```bash
write-tests --directory /path/to/source [--file /path/to/specific/file.js] [--message "custom message"]
```

**Options:** See [Common Options for All Processors](#common-options-for-all-processors)

**Example:**

```bash
# Write tests for all source files in a directory
write-tests --directory /path/to/source

# Write tests for a specific file with a custom message
write-tests --file /path/to/file.js --message "write comprehensive unit tests for this file"

# Show how files would be chunked without processing them
write-tests --directory /path/to/source --show-only-repo-files-chunks
```

### analyze-complexity

Analyzes code complexity in source files using an LLM via the `aider` tool. This script finds source files in a
specified directory and prompts `aider` to identify complex/hard-to-understand sections and suggest improvements.

**Usage:**

```bash
analyze-complexity --directory /path/to/source [--file /path/to/specific/file.py] [--message "custom analysis prompt"]
```

**Options:** See [Common Options for All Processors](#common-options-for-all-processors)

**Example:**

```bash
# Analyze complexity for all source files in a directory
analyze-complexity --directory /path/to/source

# Analyze complexity for a specific file
analyze-complexity --file /path/to/file.py

# Show how files would be chunked without processing them
analyze-complexity --directory /path/to/source --show-only-repo-files-chunks
```

### sonar-scan

Runs sonar-scanner on the entire codebase. This processor executes the sonar-scanner command-line tool to perform static
code analysis and send the results to a SonarQube server.

When running through the Docker-based wrapper (`tfc-code-pipeline --run --src /path/to/source --cmd sonar_scan`), a
`sonar-project.properties` file is automatically created in the source directory with the following content:

```
sonar.projectKey=NAME_OF_SOURCE_DIR
sonar.projectVersion=1.0
sonar.sources=.
sonar.host.url=https://sonar.thefamouscat.com
sonar.token=SONAR_TOKEN
```

Where `NAME_OF_SOURCE_DIR` is the name of the original source directory from the host (last part of the path), not the
mounted directory in Docker. The `SONAR_TOKEN` value will be replaced with the value from the `SONAR_TOKEN` environment
variable if it is set.

**Usage:**

```bash
sonar-scan --directory /path/to/source [--project-key "project-key"] [--host-url "http://sonarqube-server:9000"] [--login "auth-token"]
```

**Options:**

- All [Common Options for All Processors](#common-options-for-all-processors)
- `--project-key`: SonarQube project key
- `--host-url`: SonarQube host URL (default: http://localhost:9000)
- `--login`: SonarQube authentication token
- `--sources`: Comma-separated list of source directories to scan (relative to project root)
- `--exclusions`: Comma-separated list of file path patterns to exclude from analysis

**Example:**

```bash
# Run sonar-scanner on a directory with default settings
sonar-scan --directory /path/to/source

# Run sonar-scanner with custom project key and host URL
sonar-scan --directory /path/to/source --project-key "my-project" --host-url "http://sonarqube.example.com:9000"

# Run sonar-scanner with authentication token
sonar-scan --directory /path/to/source --login "auth-token"

# Run sonar-scanner with custom source directories and exclusions
sonar-scan --directory /path/to/source --sources "src,tests" --exclusions "**/*.test.js,**/node_modules/**"
```

### tfc-code-pipeline

A Docker-based wrapper for the other scripts. It creates a Docker container based on Python 3.12, installs Aider and the
package itself in the container, and runs the specified command with the provided messages.

**Usage:**

```bash
tfc-code-pipeline [--build-only] [--skip-build] [--run] [--src /path/to/source] [--messages "custom message"] [--cmd explain_code|write_tests|find_bugs|analyze_complexity|sonar_scan]
```

**Options:**

- `--build-only`: Only build the Docker image without running the container
- `--skip-build`: Skip building the Docker image, only run the command
- `--run`: Run the Docker container with the provided messages
- `--src`: Directory to mount in the Docker container under /src
- `--messages`: Custom message to pass to aider (default: "Hello")
- `--cmd`: Command to run in the Docker container (choices: "explain_code", "write_tests", "find_bugs", "
  analyze_complexity", or "sonar_scan", default: "explain_code")

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

# Run sonar-scan in a Docker container
tfc-code-pipeline --run --src /path/to/source --cmd sonar_scan

# Run explain-code in a Docker container, skipping the Docker image build
tfc-code-pipeline --run --skip-build --src /path/to/source --cmd explain_code
```

## Common Options for All Processors

All code processors support the following common options:

- `--directory`: Directory to search for source files (required)
- `--file`: Specific file to process (optional, overrides directory search)
- `--message`: Custom message to pass to aider (optional, defaults to processor-specific message)
- `--show-only-repo-files-chunks`: Only show the file chunks that would be processed, then exit without processing

The `--show-only-repo-files-chunks` option is particularly useful for processors with `operates_on_whole_codebase=True`
to preview how files will be grouped before running the actual processing.

**Example:**

```bash
# Show how files would be chunked without processing them
explain-code --directory /path/to/source --show-only-repo-files-chunks
```

## Logging

This project uses a centralized logging configuration to ensure consistent logging behavior across all components. The
logging utilities are provided by the `logging_utils` module.

### Basic Usage

The simplest way to get a configured logger is to use the `get_logger` function:

```python
# Get a configured logger for your module
from logging_utils import get_logger

# Get a configured logger (automatically uses your module name)
logger = get_logger()

# Now you can use the logger
logger.info("This is an info message")
```

## Environment Variables

This project supports loading environment variables from a `.env` file. When using the Docker-based approach (
`tfc-code-pipeline`), these variables are automatically passed to the Docker container.

Common environment variables:

- `OPENAI_API_KEY`: API key for OpenAI (used by Aider)
- `DEBUG`: Enable debug mode (set to "True" to enable)
- `SONAR_TOKEN`: Authentication token for SonarQube (used by sonar-scanner)

To use environment variables, create a `.env` file in the project root directory:

```
OPENAI_API_KEY=your-api-key-here
DEBUG=False
SONAR_TOKEN=your-sonar-token-here
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

## Testing

When writing tests for this project, be aware that the logger name used in the code is "tfc-code-pipeline", not the
module name. When using `assertLogs()` in tests, make sure to use the correct logger name:

```python
# Incorrect - will fail:
with self.assertLogs('find_source_files', level='INFO') as cm:
# test code

# Correct - will pass:
with self.assertLogs('tfc-code-pipeline', level='INFO') as cm:
# test code
```

## Integration with Development Workflows

Code processors can be integrated into development workflows in several ways:

1. **Local Development**: Developers can run processors on their local machines to explain code, write tests, or find
   bugs.

2. **CI/CD Pipelines**: Processors can be integrated into CI/CD pipelines to automatically analyze code, find bugs, or
   generate tests.

3. **Code Review**: Processors can be used during code review to identify potential issues or suggest improvements.

4. **Documentation**: Processors can be used to generate documentation or explanations for code.
