# Coding Conventions

This document outlines the basic coding conventions for the TFC Test Writer Aider project.

## Python Style

- Follow [PEP 8](https://www.python.org/dev/peps/pep-0008/) style guide for Python code
- Use 4 spaces for indentation (no tabs)
- Maximum line length of 88 characters
- Use snake_case for function and variable names
- Use UPPERCASE for constants
- Use CamelCase for class names

## Documentation

- All modules, classes, and functions should have docstrings
- Use triple double quotes (`"""`) for docstrings
- Module docstrings should describe the purpose of the module
- Function docstrings should describe what the function does, not how it does it

## Imports

- Imports should be at the top of the file
- Group imports in the following order:
  1. Standard library imports
  2. Related third-party imports
  3. Local application/library specific imports
- Use blank lines to separate import groups

## Code Structure

- Use two blank lines before class definitions
- Use two blank lines before top-level functions
- Use one blank line before method definitions
- Use the `if __name__ == "__main__":` pattern for executable scripts

## Comments

- Comments should explain why, not what
- Keep comments up-to-date when code changes
- Use inline comments sparingly

## Testing

- All code should have corresponding tests
- Test files should be named `test_*.py`
- Test functions should be named `test_*`
- **Mocking is not allowed in unit tests**
- Tests should be simple, focused, and independent
- Use direct assertions to verify behavior

## Error Handling

- Use explicit exception handling
- Catch specific exceptions, not `Exception`
- Provide meaningful error messages

## Version Control

- Write clear, concise commit messages
- Each commit should represent a logical change
- Keep commits focused on a single issue