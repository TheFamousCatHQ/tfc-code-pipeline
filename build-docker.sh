#!/bin/sh

poetry install
poetry run python -m tfc_code_pipeline.cli  --build-only --cmd sonar_scan --platform linux/arm64
poetry run python -m tfc_code_pipeline.cli  --build-only --cmd sonar_scan --platform linux/amd64