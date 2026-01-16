#!/usr/bin/env python3
"""
Simple script to run the batch file processor server.
Press Ctrl+C to stop the server gracefully.
"""

import signal
import sys
import subprocess
import os
from pathlib import Path


def signal_handler(sig, frame):
    print("\nShutting down server...")
    sys.exit(0)


def main():
    # Set up signal handler for graceful shutdown
    signal.signal(signal.SIGINT, signal_handler)

    try:
        print("Starting Batch File Processor Server...")
        print("Press Ctrl+C to stop the server")
        print()

        # Set up virtual environment if needed
        project_root = Path(__file__).parent
        venv_path = project_root / ".venv"

        # Create virtual environment if it doesn't exist
        if not venv_path.exists():
            print("Creating virtual environment...")
            subprocess.check_call([sys.executable, "-m", "venv", str(venv_path)])

        # Set DATABASE_PATH to a writable location if not already set
        if "DATABASE_PATH" not in os.environ:
            os.environ["DATABASE_PATH"] = "./folders_local.db"

        # Import and run directly
        sys.path.insert(0, str(project_root))
        from backend.main import app
        import uvicorn

        # Run the server
        uvicorn.run(
            app,
            host="0.0.0.0",
            port=8000,
            reload=False,
            log_level="info"
        )

    except KeyboardInterrupt:
        print("\nShutting down server...")
    except Exception as e:
        print(f"Error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()