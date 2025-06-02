#!/bin/sh

# Install dependencies
poetry install

# Generate Dockerfile
poetry run python -m tfc_code_pipeline.cli --generate-dockerfile

docker build -t tfc-code-pipeline
