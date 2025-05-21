#!/usr/bin/env bash

# Usage: ./run_docker_image.sh [--debug] [--working-tree] [--commit COMMIT_HASH]

IMAGE_NAME="tfccodepipeline/app:latest"
SRC_DIR=$(pwd)
EXTRA_ARGS=()
ENTRYPOINT="fix-bugs"

# Read .env and export as -e flags
ENV_FLAGS=()
if [ -f .env ]; then
  while IFS='=' read -r key value; do
    # Skip comments and empty lines
    [[ "$key" =~ ^#.*$ || -z "$key" ]] && continue
    ENV_FLAGS+=("-e" "$key=$value")
  done < .env
fi

# Always set ORIGINAL_SRC_DIR_NAME
ENV_FLAGS+=("-e" "ORIGINAL_SRC_DIR_NAME=$(basename "$SRC_DIR")")

# Parse arguments
while [[ $# -gt 0 ]]; do
  EXTRA_ARGS+=("$1")
  shift
done

docker run --rm -it \
  "${ENV_FLAGS[@]}" \
  -v "$SRC_DIR:/src" \
  --entrypoint "$ENTRYPOINT" \
  "$IMAGE_NAME" \
  "${EXTRA_ARGS[@]}" 