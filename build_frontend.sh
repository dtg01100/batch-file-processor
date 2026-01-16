#!/bin/bash

# Build script for the React frontend

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
FRONTEND_DIR="$SCRIPT_DIR/frontend"

echo "Building Batch File Processor Frontend..."
echo

cd "$FRONTEND_DIR" || exit 1

# Check if node_modules exists
if [ ! -d "node_modules" ]; then
    echo "Installing npm dependencies..."
    npm install
    echo
fi

echo "Building React app..."
npm run build

if [ $? -eq 0 ]; then
    echo
    echo "✓ Frontend build complete!"
    echo "✓ Built files are in: $FRONTEND_DIR/dist"
    echo
    echo "Start the server with: ./run_server.sh or python3 run_server.py"
else
    echo
    echo "✗ Build failed!"
    exit 1
fi
