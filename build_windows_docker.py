#!/usr/bin/env python3
"""
Windows build script that creates a Docker image with all source files
and builds the Windows executable without relying on volume mounts.
"""

import sys
import subprocess
import shutil
from pathlib import Path

def main():
    project_root = Path(__file__).parent.absolute()
    dist_dir = project_root / "dist"

    # Clean previous builds
    if dist_dir.exists():
        shutil.rmtree(dist_dir)

    print("Creating Dockerfile for Windows build...")

    dockerfile_content = '''
FROM docker.io/batonogov/pyinstaller-windows:v4.0.1

# Install git (needed for some dependencies)
RUN apt-get update && apt-get install -y git

# Copy all project files
COPY . /src/

# Set working directory
WORKDIR /src

# Ensure spec file exists
RUN ls -la /src/main_interface.spec

# Set environment variable for the original entrypoint
ENV SPECFILE=/src/main_interface.spec
'''

    with open(project_root / "Dockerfile.windows.build", "w") as f:
        f.write(dockerfile_content)

    print("Building Docker image...")
    try:
        # Build the Docker image
        subprocess.run([
            "sudo", "docker", "build",
            "-f", "Dockerfile.windows.build",
            "-t", "batch-file-processor-windows-build",
            "."
        ], cwd=project_root, check=True)

        print("Running build container...")
        # Run the container to build the executable
        subprocess.run([
            "sudo", "docker", "run",
            "--rm",
            "batch-file-processor-windows-build"
        ], cwd=project_root, check=True)

        print("Extracting built executable...")
        # Create a temporary container to extract files
        container_id = subprocess.check_output([
            "sudo", "docker", "create",
            "batch-file-processor-windows-build"
        ], cwd=project_root, text=True).strip()

        try:
            # Copy the dist directory from the container
            subprocess.run([
                "sudo", "docker", "cp",
                f"{container_id}:/src/dist",
                str(project_root)
            ], cwd=project_root, check=True)

            print("Cleaning up...")
            subprocess.run([
                "sudo", "docker", "rm", container_id
            ], cwd=project_root, check=True)

        except Exception as e:
            subprocess.run([
                "sudo", "docker", "rm", container_id
            ], cwd=project_root, check=False)
            raise e

        # Verify the build
        if (dist_dir / "Batch File Sender" / "Batch File Sender.exe").exists():
            print("✅ Windows build completed successfully!")
            print(f"Executable location: {dist_dir}/Batch File Sender/Batch File Sender.exe")
        else:
            print("❌ Build completed but executable not found")
            if dist_dir.exists():
                print("Contents of dist directory:")
                for item in dist_dir.rglob("*"):
                    print(f"  {item}")

    except subprocess.CalledProcessError as e:
        print(f"❌ Build failed with error: {e}")
        sys.exit(1)
    except Exception as e:
        print(f"❌ Unexpected error: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()