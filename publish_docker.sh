#!/bin/bash

# Script to build and publish the TFC Code Pipeline Docker image to DockerHub
# Usage: ./publish_docker.sh [tag]
# If no tag is provided, "latest" will be used

# Exit on any error
set -e

# Configuration
DOCKER_REPO="tfc-code-pipeline"
DEFAULT_TAG="latest"
TAG=${1:-$DEFAULT_TAG}

# Check if Docker is installed
if ! command -v docker &> /dev/null; then
    echo "Error: Docker is not installed or not in PATH"
    exit 1
fi

# Check if user is logged in to DockerHub
echo "Checking Docker login status..."
if ! docker info | grep -q "Username"; then
    echo "You are not logged in to DockerHub. Please login:"
    docker login
fi

# Get username from Docker config
USERNAME=$(docker info | grep Username | cut -d: -f2 | tr -d '[:space:]')
if [ -z "$USERNAME" ]; then
    echo "Could not determine Docker username. Please make sure you're logged in."
    exit 1
fi

FULL_IMAGE_NAME="$USERNAME/$DOCKER_REPO:$TAG"

echo "Building Docker image: $FULL_IMAGE_NAME"
echo "This will exclude files specified in .dockerignore, including .env files"

# Build the Docker image
docker build -t "$FULL_IMAGE_NAME" .

echo "Docker image built successfully"
echo "Pushing image to DockerHub..."

# Push the image to DockerHub
docker push "$FULL_IMAGE_NAME"

echo "Image pushed successfully to DockerHub as $FULL_IMAGE_NAME"
echo ""
echo "Users can pull this image with:"
echo "  docker pull $FULL_IMAGE_NAME"
echo ""
echo "To run the image with your own API keys:"
echo "  docker run --rm -v \$(pwd):/src -e OPENAI_API_KEY=your_key -e ANTHROPIC_API_KEY=your_key $FULL_IMAGE_NAME [command]"
echo ""
echo "Or using an .env file:"
echo "  docker run --rm -v \$(pwd):/src --env-file .env $FULL_IMAGE_NAME [command]"