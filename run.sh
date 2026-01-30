#!/bin/bash

# Batch File Processor - Run Script
# Usage: ./run.sh [options]
#   -a, --automatic    Run in automatic mode (no GUI)
#   -h, --help         Show this help message

set -e # Exit on error

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Get script directory
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

# Print colored message
print_info() {
	echo -e "${GREEN}[INFO]${NC} $1"
}

print_error() {
	echo -e "${RED}[ERROR]${NC} $1"
}

print_warning() {
	echo -e "${YELLOW}[WARNING]${NC} $1"
}

# Show help
show_help() {
	echo "Batch File Processor - Run Script"
	echo ""
	echo "Usage: ./run.sh [options]"
	echo ""
	echo "Options:"
	echo "  -a, --automatic    Run in automatic mode (no GUI)"
	echo "  -h, --help         Show this help message"
	echo ""
	echo "Examples:"
	echo "  ./run.sh           # Run in GUI mode"
	echo "  ./run.sh -a        # Run in automatic mode"
}

# Check if help requested
if [[ "$1" == "-h" ]] || [[ "$1" == "--help" ]]; then
	show_help
	exit 0
fi

# Check if Python 3 is available
if ! command -v python3 &>/dev/null; then
	print_error "Python 3 is not installed or not in PATH"
	exit 1
fi

# Check if virtual environment exists
if [ ! -d ".venv" ]; then
	print_warning "Virtual environment not found at .venv"
	print_info "Creating virtual environment..."
	python3 -m venv .venv

	print_info "Installing dependencies..."
	source .venv/bin/activate
	pip install --upgrade pip
	pip install -r requirements.txt
else
	print_info "Using existing virtual environment"
fi

# Activate virtual environment
print_info "Activating virtual environment..."
source .venv/bin/activate

# Verify Python version
PYTHON_VERSION=$(python --version 2>&1 | awk '{print $2}')
print_info "Python version: $PYTHON_VERSION"

# Check if requirements are installed
if ! python -c "import PyQt6" 2>/dev/null; then
	print_warning "Dependencies not installed"
	print_info "Installing dependencies..."
	pip install -r requirements.txt
fi

# Run the application
print_info "Starting Batch File Processor..."
echo ""

if [[ "$1" == "-a" ]] || [[ "$1" == "--automatic" ]]; then
	print_info "Running in automatic mode (no GUI)"
	python interface/main.py --automatic
else
	print_info "Running in GUI mode"
	python interface/main.py "$@"
fi

# Exit status
EXIT_CODE=$?
echo ""
if [ $EXIT_CODE -eq 0 ]; then
	print_info "Application exited successfully"
else
	print_error "Application exited with code $EXIT_CODE"
fi

exit $EXIT_CODE
