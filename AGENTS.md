# Agent Development Guide

## Python Virtual Environment

**IMPORTANT**: This project requires a Python virtual environment for development and testing.

### Setup

A virtual environment (`.venv`) must be activated before running development or testing commands:

```bash
# Activate the virtual environment
source .venv/bin/activate  # Linux/macOS
.venv\Scripts\activate     # Windows

# Verify activation (should show .venv in path)
which python
```

### Why Virtual Environments?

- **Dependency Isolation**: Prevents conflicts with system Python packages
- **Version Control**: Ensures consistent package versions across environments
- **Testing Accuracy**: Tests run with the exact dependencies specified in `requirements.txt`
- **Reproducibility**: Other developers/agents get the same environment

### Common Commands (with venv)

All development and testing commands assume the virtual environment is active:

```bash
# Run the application
./run.sh

# Run tests
./run_tests.sh

# Install/update dependencies
pip install -r requirements.txt
```

### For Automated Agents

When executing Python commands programmatically:

1. **Always activate the virtual environment first** in your shell session
2. Use `source .venv/bin/activate` before running any Python commands
3. Check activation status with `which python` (should point to `.venv/bin/python`)
4. If running commands via scripts, ensure they activate the venv internally (like `run.sh` and `run_tests.sh` do)

### Troubleshooting

If you encounter import errors or version mismatches:

```bash
# Deactivate current environment
deactivate

# Reactivate
source .venv/bin/activate

# Reinstall dependencies
pip install -r requirements.txt
```
