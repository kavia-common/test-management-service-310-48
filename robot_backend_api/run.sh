#!/bin/bash
# Startup script for Robot Framework Test Management API

# Set the working directory to the script's directory
cd "$(dirname "$0")"

# Add src directory to PYTHONPATH
export PYTHONPATH="${PYTHONPATH}:$(pwd)/src"

# Run uvicorn with the correct module path
uvicorn api.main:app --host 0.0.0.0 --port 8000 --reload
