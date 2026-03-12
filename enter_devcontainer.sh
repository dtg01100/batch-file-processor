#!/bin/bash
#
# Script to enter the devcontainer using the devcontainer CLI
#

set -e

# Check if devcontainer CLI is available
if ! command -v devcontainer &> /dev/null; then
    echo "Error: devcontainer CLI not found."
    echo "Please install it: https://code.visualstudio.com/docs/devcontainers/devcontainer-cli"
    exit 1
fi

# Get the directory of this script (project root)
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

# Build and start the devcontainer (if not already running)
echo "Building and starting devcontainer..."
devcontainer up --workspace-folder "$SCRIPT_DIR"

# Execute shell in the container
echo "Entering devcontainer shell..."
devcontainer exec --workspace-folder "$SCRIPT_DIR" bash
