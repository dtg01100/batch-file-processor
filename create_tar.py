#!/usr/bin/env python3
import sys
import tarfile
import os

def create_tar():
    """Create tar stream from /src/dist directory to stdout"""
    try:
        with tarfile.open(fileobj=sys.stdout.buffer, mode='w|') as tar:
            if os.path.exists('/src/dist'):
                tar.add('/src/dist', arcname='dist')
                print("Tar creation completed successfully", file=sys.stderr)
            else:
                print("Warning: /src/dist does not exist", file=sys.stderr)
    except Exception as e:
        print(f"Tar creation failed: {e}", file=sys.stderr)
        sys.exit(1)

if __name__ == "__main__":
    create_tar()