#!/usr/bin/env python3
"""
Windows build script that creates a Docker image with all source files
and builds the Windows executable without relying on volume mounts.
"""

import os
import sys
import subprocess
import tempfile
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

# Install Python dependencies
RUN pip install -r requirements.txt

# Run PyInstaller and copy output to /src/dist
RUN pyinstaller main_interface.spec --noconfirm --clean
'''
    
    with open(project_root / "Dockerfile.windows.build", "w") as f:
        f.write(dockerfile_content)
    
    print("Building Docker image (this includes running PyInstaller)...")
    try:
        # Build the Docker image (this runs PyInstaller as part of the build)
        subprocess.run([
            "docker", "build", 
            "-f", "Dockerfile.windows.build",
            "-t", "batch-file-processor-windows-build",
            "."
        ], cwd=project_root, check=True)
        
        print("Extracting built executable from container...")
        # Create a temporary container to extract files
        container_id = subprocess.check_output([
            "docker", "create", 
            "batch-file-processor-windows-build"
        ], cwd=project_root, text=True).strip()
        
        try:
            # Copy the dist directory from the container
            subprocess.run([
                "docker", "cp", 
                f"{container_id}:/src/dist",
                str(project_root)
            ], cwd=project_root, check=True)
            
            print("Cleaning up...")
            subprocess.run([
                "docker", "rm", container_id
            ], cwd=project_root, check=True)
            
        except Exception as e:
            subprocess.run([
                "docker", "rm", container_id
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