#!/bin/bash

# Simple script to run the batch file processor server with virtual environment
# Press Ctrl+C to stop the server gracefully

PROJECT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
VENV_PATH="$PROJECT_ROOT/.venv"
PYTHON_EXECUTABLE="$VENV_PATH/bin/python"

echo "Starting Batch File Processor Server..."
echo "Press Ctrl+C to stop the server"
echo

# Check if virtual environment exists, create if not
if [ ! -d "$VENV_PATH" ]; then
    echo "Creating virtual environment..."
    python3 -m venv "$VENV_PATH"
fi

# Activate virtual environment for current shell
source "$VENV_PATH/bin/activate"

# Set the database path to a writable location
export DATABASE_PATH="./folders_local.db"

# Run the server using the virtual environment's Python
"$PYTHON_EXECUTABLE" -c "
import os
import uvicorn
from backend.main import app

# Set the database path programmatically
os.environ['DATABASE_PATH'] = './folders_local.db'
uvicorn.run(app, host='0.0.0.0', port=8000, reload=False)
"