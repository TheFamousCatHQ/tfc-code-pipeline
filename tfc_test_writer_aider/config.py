"""Configuration module for TFC Test Writer Aider."""

import os
from pathlib import Path
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

# Base directory of the project
BASE_DIR = Path(__file__).parent.parent

# Debug mode
DEBUG = os.getenv("DEBUG", "False").lower() in ("true", "1", "t")
