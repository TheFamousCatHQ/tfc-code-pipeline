#!/bin/sh

poetry install
poetry run python -m tfc_code_pipeline.cli  --build-only --cmd sonar_scan
