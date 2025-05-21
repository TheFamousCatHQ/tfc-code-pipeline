#!/bin/bash

# Simple wrapper script for running TFC Code Pipeline in Docker
# Usage: ./run-tfc-pipeline.sh [command] [args...]
# Example: ./run-tfc-pipeline.sh bug-analyzer --working-tree

# Exit on any error
set -e

# Configuration
DOCKER_IMAGE="tfc-code-pipeline:python3.12"
ENV_FILE=".env"
SRC_DIR="$(pwd)"

# Check if Docker is installed
if ! command -v docker &> /dev/null; then
    echo "Error: Docker is not installed or not in PATH"
    exit 1
fi

# Check if .env file exists
if [ ! -f "$ENV_FILE" ]; then
    echo "Warning: No .env file found at $ENV_FILE"
    echo "You will need to provide API keys as environment variables."
    echo "See .env.example for required variables."
    
    # Ask user if they want to continue
    read -p "Continue without .env file? (y/n): " -n 1 -r
    echo
    if [[ ! $REPLY =~ ^[Yy]$ ]]; then
        exit 1
    fi
    
    # No .env file, use empty env vars
    ENV_ARGS=""
else
    # Use .env file
    ENV_ARGS="--env-file $ENV_FILE"
fi

# Check if a command was provided
if [ $# -eq 0 ]; then
    echo "Error: No command specified"
    echo "Usage: $0 [command] [args...]"
    echo "Available commands: find-source-files, explain-code, write-tests, find-bugs,"
    echo "                   analyze-complexity, sonar-scan, sonar-analyze, bug-analyzer, fix-bugs"
    exit 1
fi

COMMAND="$1"
shift  # Remove the command from the arguments

# Check if the image exists locally
if ! docker image inspect "$DOCKER_IMAGE" &> /dev/null; then
    echo "Docker image $DOCKER_IMAGE not found locally."
    echo "You may need to build it first with:"
    echo "  poetry run python -m tfc_code_pipeline.cli --build-only"
    exit 1
fi

# Run the Docker container
echo "Running $COMMAND in Docker container..."
docker run --rm -it \
    -v "$SRC_DIR:/src" \
    $ENV_ARGS \
    --entrypoint "$COMMAND" \
    "$DOCKER_IMAGE" \
    --directory /src "$@"

echo "Command completed."