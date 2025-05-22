# Code Processor Framework

This framework provides a common base class for processing code files using AI tools.

## Docker Usage

The easiest way to use TFC Code Pipeline is with the pre-built Docker image.

### Quick Start

```bash
# Run the bug-analyzer tool with your API key
docker run -it -e OPENROUTER_API_KEY -v .:/src --entrypoint bug-analyzer ghcr.io/thefamouscathq/tfc-code-pipeline --directory /src
```

### Available Tools

The Docker image includes several tools:

- `bug-analyzer`: Analyzes code changes to identify potential bugs
- `fix-bugs`: Fixes bugs identified by bug-analyzer
- `find-bugs`: Finds potential bugs in source files
- `explain-code`: Explains code in source files
- `write-tests`: Writes unit tests for source files
- `analyze-complexity`: Analyzes code complexity
- `sonar-scan`: Runs Sonar scanner
- `sonar-analyze`: Analyzes Sonar scanner reports
- `find-source-files`: Finds source files in a directory

### Environment Variables

The following environment variables can be passed to the Docker container:

- `OPENAI_API_KEY`: API key for OpenAI (used by Aider and other AI-powered processors)
- `ANTHROPIC_API_KEY`: API key for Anthropic (used by some AI-powered processors)
- `OPENROUTER_API_KEY`: API key for OpenRouter (used by bug-analyzer and other AI-powered processors)
- `DEBUG`: Enable debug mode (set to "True" to enable)
- `SONAR_TOKEN`: Authentication token for SonarQube (used by sonar-scanner)

You can pass environment variables directly using the `-e` flag:

```bash
docker run -it -e OPENROUTER_API_KEY=your_key -v .:/src --entrypoint bug-analyzer ghcr.io/thefamouscathq/tfc-code-pipeline --directory /src
```

Alternatively, you can use an environment file with the `--env-file` flag:

```bash
# Create a .env file with your API keys
echo "OPENAI_API_KEY=your_openai_key" > .env
echo "ANTHROPIC_API_KEY=your_anthropic_key" >> .env
echo "OPENROUTER_API_KEY=your_openrouter_key" >> .env

# Run with the environment file
docker run -it --env-file .env -v .:/src --entrypoint bug-analyzer ghcr.io/thefamouscathq/tfc-code-pipeline --directory /src
```

The framework will automatically look for a `.env` file in the current directory when running outside of Docker.

### Volume Mounting

Mount your source code directory to `/src` in the container:

```bash
docker run -it -e OPENROUTER_API_KEY -v /path/to/your/code:/src --entrypoint bug-analyzer ghcr.io/thefamouscathq/tfc-code-pipeline --directory /src
```

### Examples

#### Analyze bugs in working tree changes

```bash
docker run -it -e OPENROUTER_API_KEY -v .:/src --entrypoint bug-analyzer ghcr.io/thefamouscathq/tfc-code-pipeline --working-tree
```

#### Find bugs in source files

```bash
docker run -it -e OPENROUTER_API_KEY -v .:/src --entrypoint find-bugs ghcr.io/thefamouscathq/tfc-code-pipeline --directory /src
```

#### Explain code in source files

```bash
docker run -it -e OPENROUTER_API_KEY -v .:/src --entrypoint explain-code ghcr.io/thefamouscathq/tfc-code-pipeline --directory /src
```

#### Write tests for source files

```bash
docker run -it -e OPENROUTER_API_KEY -v .:/src --entrypoint write-tests ghcr.io/thefamouscathq/tfc-code-pipeline --directory /src
```

#### Analyze code complexity

```bash
docker run -it -e OPENROUTER_API_KEY -v .:/src --entrypoint analyze-complexity ghcr.io/thefamouscathq/tfc-code-pipeline --directory /src
```

#### Run Sonar scanner

```bash
docker run -it -e SONAR_TOKEN -v .:/src --entrypoint sonar-scan ghcr.io/thefamouscathq/tfc-code-pipeline --directory /src
```

## Tool Documentation

### Sonar Analyzer

The `sonar-analyze` tool analyzes Sonar scanner reports and generates improvement suggestions for each component/file,
including prompts suitable for AI Coding Agents. It processes both issues and file complexity measures.

#### Usage

```bash
docker run -it -v .:/src --entrypoint sonar-analyze ghcr.io/thefamouscathq/tfc-code-pipeline --report-file /src/path/to/sonar/report.json [--min-severity SEVERITY] [--output-file /src/path/to/output.json]
```

#### Options

- `--report-file`: Path to the Sonar scanner report JSON file (required)
- `--min-severity`: Minimum severity level to include in the analysis (default: MEDIUM)
    - Available options: LOW, INFO, MEDIUM, HIGH, BLOCKER
- `--output-file`: Path to the output file for the analysis results (default: stdout)

### Bug Analyzer

The `bug-analyzer` tool analyzes code changes to identify potential bugs. It can operate in two modes:

1. **Commit mode**: Analyzes the diff of a specific commit
2. **Working tree mode**: Analyzes the diff between the working tree and HEAD

#### Usage

```bash
docker run -it -e OPENROUTER_API_KEY -v .:/src --entrypoint bug-analyzer ghcr.io/thefamouscathq/tfc-code-pipeline [--commit COMMIT_ID] [--working-tree] [--output /src/OUTPUT_FILE]
```

#### Options

- `--commit`: Commit ID to analyze (default: HEAD, used only if --working-tree is not specified)
- `--working-tree`: Analyze diff between working tree and HEAD instead of a specific commit
- `--output`: Output file path for the bug analysis report (default: bug_analysis_report.xml)

### Fix Bugs

The `fix-bugs` tool takes a bug analysis report (XML) and uses AI to automatically fix the identified bugs.

#### Usage

```bash
docker run -it -e OPENAI_API_KEY -v .:/src --entrypoint fix-bugs ghcr.io/thefamouscathq/tfc-code-pipeline [--skip-bug-analyzer] [--output /src/bug_analysis_report.xml] [--auto-commit]
```

#### Options

- `--skip-bug-analyzer`: Skip running bug_analyzer and use the provided --output XML file directly
- `--output`: Path to the bug analysis report XML file (default: bug_analysis_report.xml)
- `--working-tree`: Analyze diff between working tree and HEAD (default: False)
- `--commit`: Commit ID to analyze (optional, overrides working tree if provided)
- `--auto-commit`: Automatically commit the changes after fixing the bugs
- `--debug`: Run with additional debug output

### Find Bugs and Fix

The `find-bugs-and-fix` tool combines bug analysis and fixing in an interactive workflow. It runs the bug analyzer, displays each bug with details, and prompts you to apply fixes one by one.

#### Usage

```bash
docker run -it -e OPENAI_API_KEY -v .:/src --entrypoint find-bugs-and-fix ghcr.io/thefamouscathq/tfc-code-pipeline [--commit COMMIT_ID] [--working-tree] [--directory /src] [--output /src/bug_analysis_report.xml]
```

#### Options

- `--commit`: Commit ID to analyze (default: HEAD)
- `--working-tree`: Analyze diff between working tree and HEAD instead of a specific commit
- `--directory`: Directory to analyze (default: /src)
- `--output`: Output file path for the bug analysis report (default: bug_analysis_report.xml)
- `--debug`: Enable debug mode with additional output

## Development

For information on developing this project, including how to set up a local development environment, create new processors, and run tests, please see [DEVELOPMENT.md](DEVELOPMENT.md).

## Coding Conventions

For coding conventions used in this project, please see [CONVENTIONS.md](CONVENTIONS.md).
