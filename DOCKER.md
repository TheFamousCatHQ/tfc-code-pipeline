# Docker Usage for TFC Code Pipeline

This document provides instructions for using the TFC Code Pipeline with Docker.

## Quick Start

The easiest way to use TFC Code Pipeline is with the pre-built Docker image:

```bash
# Pull the image
docker pull yourusername/tfc-code-pipeline:latest

# Run a command (e.g., find-bugs)
docker run --rm -v $(pwd):/src --env-file .env yourusername/tfc-code-pipeline:latest find-bugs --directory /src
```

## Environment Variables

The TFC Code Pipeline requires several API keys to function properly. These can be provided in two ways:

1. **Using an .env file** (recommended):
   ```bash
   docker run --rm -v $(pwd):/src --env-file .env yourusername/tfc-code-pipeline:latest [command]
   ```

2. **Passing environment variables directly**:
   ```bash
   docker run --rm -v $(pwd):/src \
     -e OPENAI_API_KEY=your_key \
     -e ANTHROPIC_API_KEY=your_key \
     yourusername/tfc-code-pipeline:latest [command]
   ```

See `.env.example` for a list of all required environment variables.

## Available Commands

The Docker image supports all the commands available in the TFC Code Pipeline:

- `find-source-files`: Find source files in a directory
- `explain-code`: Explain code in source files
- `write-tests`: Write unit tests for source files
- `find-bugs`: Find potential bugs in source files
- `analyze-complexity`: Analyze code complexity
- `sonar-scan`: Run Sonar scanner
- `sonar-analyze`: Analyze Sonar scanner reports
- `bug-analyzer`: Analyze bugs in code changes
- `fix-bugs`: Fix bugs identified by bug-analyzer

Example:
```bash
docker run --rm -v $(pwd):/src --env-file .env yourusername/tfc-code-pipeline:latest bug-analyzer --working-tree --output /src/bug_report.xml
```

## Building the Docker Image

If you want to build the Docker image yourself:

```bash
# Clone the repository
git clone https://github.com/yourusername/tfc-code-pipeline.git
cd tfc-code-pipeline

# Build the image
docker build -t yourusername/tfc-code-pipeline:latest .
```

The build process uses the `.dockerignore` file to exclude sensitive files like `.env` from the image.

## Publishing to DockerHub

To publish the image to DockerHub, you can use the provided script:

```bash
# Make the script executable (if not already)
chmod +x publish-docker.sh

# Publish with default tag (latest)
./publish-docker.sh

# Or specify a custom tag
./publish-docker.sh v1.0.0
```

The script will:
1. Check if Docker is installed
2. Verify you're logged in to DockerHub
3. Build the image with the appropriate tag
4. Push the image to DockerHub

## Using with the Main CLI

You can also use the main CLI interface through Docker:

```bash
docker run --rm -v $(pwd):/src --env-file .env yourusername/tfc-code-pipeline:latest tfc-code-pipeline --cmd bug_analyzer --working-tree --output /src/bug_report.xml
```

## Security Notes

- **Never** include your `.env` file in the Docker image
- The `.dockerignore` file is configured to exclude `.env` and other sensitive files
- Always use the `--env-file` flag or pass environment variables with `-e` when running the container
- Verify that your API keys are not being stored in the Docker image

## Troubleshooting

If you encounter issues:

1. **Missing API keys**: Ensure your `.env` file contains all required API keys
2. **Permission issues**: Make sure the mounted directory has appropriate permissions
3. **Docker errors**: Verify Docker is installed and running correctly