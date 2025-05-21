#!/usr/bin/env bash

# Usage: ./run_fix_bugs.sh [--env-file ENVFILE] [--debug] [--working-tree] [--commit COMMIT_HASH]

IMAGE_NAME="tfccodepipeline/app:latest"
SRC_DIR=$(pwd)
EXTRA_ARGS=()
ENTRYPOINT="fix-bugs"
ENV_FILE=".env"

# Parse arguments for --env-file
while [[ $# -gt 0 ]]; do
  case $1 in
    --env-file)
      ENV_FILE="$2"
      shift 2
      ;;
    *)
      EXTRA_ARGS+=("$1")
      shift
      ;;
  esac
done

# Read env file and export as -e flags
ENV_FLAGS=()
if [ -f "$ENV_FILE" ]; then
  while IFS='=' read -r key value; do
    # Skip comments and empty lines
    [[ "$key" =~ ^#.*$ || -z "$key" ]] && continue
    ENV_FLAGS+=("-e" "$key=$value")
  done < "$ENV_FILE"
fi

# Always set ORIGINAL_SRC_DIR_NAME
ENV_FLAGS+=("-e" "ORIGINAL_SRC_DIR_NAME=$(basename "$SRC_DIR")")

docker run --rm -it \
  "${ENV_FLAGS[@]}" \
  -v "$SRC_DIR:/src" \
  --entrypoint "$ENTRYPOINT" \
  "$IMAGE_NAME" \
  "${EXTRA_ARGS[@]}" 