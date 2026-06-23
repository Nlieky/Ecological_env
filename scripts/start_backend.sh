#!/bin/bash
echo "Starting FastAPI Backend for Hermes Agent System..."
cd "$(dirname "$0")/.."

# Start service
python -m uvicorn backend.main:app --host 0.0.0.0 --port 8000 --reload
