#!/bin/bash
set -e  # Exit immediately if a command exits with a non-zero status
if [ "$1" = "test" ]; then
    pytest -v
    exit $?
elif [ "$1" = "test-cov" ]; then
    pytest -v --cov=src --cov-report=term-missing
    exit $?
else
    # Check if uvicorn is available
    command -v uvicorn >/dev/null 2>&1 || { echo "uvicorn command not found"; exit 1; }
    uvicorn src.main:app --host 0.0.0.0 --port 8000
fi