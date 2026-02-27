#!/usr/bin/env python3
import sys
import tarfile
import os

def extract_tar():
    """Extract tar stream from stdin to /src directory"""
    os.makedirs('/src', exist_ok=True)
    try:
        with tarfile.open(fileobj=sys.stdin.buffer, mode='r|*') as tar:
            tar.extractall('/src')
        print("Extraction completed successfully", file=sys.stderr)
    except Exception as e:
        print(f"Extraction failed: {e}", file=sys.stderr)
        sys.exit(1)

if __name__ == "__main__":
    extract_tar()