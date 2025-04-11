# Write Token Utils Tests

This tool is designed to automatically write unit tests for the `tokenUtils.js` file using Aider.

## Overview

The `write-token-utils-tests` script:

1. Searches for `tokenUtils.js` in the specified directory (recursively)
2. Uses Aider to generate unit tests without mocks for all functions in the file
3. If tests already exist, it will check if they are up to date and update them if needed

## Usage

### Direct Usage

```bash
# Install the package
pip install -e .

# Run the script
write-token-utils-tests --directory /path/to/your/project
```

### Docker Usage

```bash
# Build the Docker image
tfc-test-writer --build-only

# Run the script in Docker
docker run --rm -it -v /path/to/your/project:/src --entrypoint write-token-utils-tests tfc-test-writer-aider:python3.12 --directory "/src"
```

## Features

- Automatically finds `tokenUtils.js` in the specified directory
- Generates comprehensive unit tests without using mocks
- Updates existing tests if they are out of date
- Ensures all functions in `tokenUtils.js` are covered by tests

## Requirements

- Python 3.11 or higher
- Aider Chat installed (`pip install aider-chat`)
- Docker (for Docker usage)

## Notes

- The script follows the TFC coding conventions, particularly the requirement to not use mocks in unit tests
- Tests are written to be simple, focused, and independent
- Direct assertions are used to verify behavior
