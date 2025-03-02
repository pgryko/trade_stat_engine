#!/bin/bash

if [ "$1" = "test" ]; then
    pytest -v
elif [ "$1" = "test-cov" ]; then
    pytest -v --cov=src --cov-report=term-missing
else
    uvicorn src.main:app --host 0.0.0.0 --port 8000
fi