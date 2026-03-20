#!/usr/bin/env python3
"""
Windows build script that uses Podman to create a Windows executable.
This version does not require sudo.
"""

import shutil
import subprocess
import sys
from pathlib import Path


def main():
    project_root = Path(__file__).parent.absolute()
    dist_dir = project_root / "dist"

    # Clean previous builds
    if dist_dir.exists():
        print("Cleaning previous build...")
        shutil.rmtree(dist_dir)

    print("Creating Dockerfile for Windows build...")

    # Updated Dockerfile with proper PyInstaller command using Python 3.11
    dockerfile_content = """FROM docker.io/batonogov/pyinstaller-windows:v4.0.1

# Install git and Python 3.11
RUN apt-get update && apt-get install -y git software-properties-common && \
    add-apt-repository -y ppa:deadsnakes/ppa && \
    apt-get update && \
    apt-get install -y python3.11 python3.11-venv python3.11-dev && \
    curl -sS https://bootstrap.pypa.io/get-pip.py | python3.11

# Copy all project files
COPY . /src/

# Set working directory
WORKDIR /src

# Ensure Python 3.11 is used and install dependencies
RUN python3.11 -m pip install --upgrade pip && \
    python3.11 -m pip install pyinstaller && \
    python3.11 -m pip install -r requirements.txt

# Ensure spec file exists
RUN ls -la /src/main_interface.spec

# Run PyInstaller with Python 3.11
RUN python3.11 -m PyInstaller main_interface.spec --clean --noconfirm
"""

    dockerfile_path = project_root / "Dockerfile.windows.build"
    with open(dockerfile_path, "w") as f:
        f.write(dockerfile_content)

    print("Building container image with Podman...")
    print("This may take several minutes on first run (downloading base image)...")
    try:
        # Build the container image with live output
        result = subprocess.run(
            [
                "podman",
                "build",
                "--progress=plain",
                "-f",
                "Dockerfile.windows.build",
                "-t",
                "batch-file-processor-windows-build",
                ".",
            ],
            cwd=project_root,
            check=True,
        )
        print("Container image built successfully!")

        print("Running build container...")
        print("PyInstaller is building the Windows executable with Python 3.11...")
        # Run the container to build the executable with live output
        result = subprocess.run(
            ["podman", "run", "--rm", "batch-file-processor-windows-build"],
            cwd=project_root,
            check=True,
        )
        print("Build container completed!")

        print("Extracting built executable...")
        # Create a temporary container to extract files
        container_id = subprocess.check_output(
            ["podman", "create", "batch-file-processor-windows-build"],
            cwd=project_root,
            text=True,
        ).strip()

        try:
            # Copy the dist directory from the container
            subprocess.run(
                ["podman", "cp", f"{container_id}:/src/dist", str(project_root)],
                cwd=project_root,
                check=True,
            )

            print("Cleaning up temporary container...")
            subprocess.run(
                ["podman", "rm", container_id],
                cwd=project_root,
                check=True,
            )

        except Exception as e:
            subprocess.run(
                ["podman", "rm", container_id],
                cwd=project_root,
                check=False,
            )
            raise e

        # Verify the build
        exe_path = dist_dir / "Batch File Sender" / "Batch File Sender.exe"
        if exe_path.exists():
            print("=" * 60)
            print("✅ Windows build completed successfully!")
            print("=" * 60)
            print(f"Executable location: {exe_path}")
            size = exe_path.stat().st_size
            print(f"Executable size: {size:,} bytes ({size / 1024 / 1024:.2f} MB)")

            # List all files in the dist directory
            print("\nBuild artifacts:")
            for item in sorted(dist_dir.rglob("*")):
                rel_path = item.relative_to(dist_dir)
                if item.is_file():
                    file_size = item.stat().st_size
                    print(f"  {rel_path} ({file_size / 1024:.1f} KB)")
                else:
                    print(f"  {rel_path}/")

            # Clean up Dockerfile
            if dockerfile_path.exists():
                dockerfile_path.unlink()
                print("\nCleaned up temporary Dockerfile")

            return 0
        else:
            print("❌ Build completed but executable not found")
            if dist_dir.exists():
                print("\nContents of dist directory:")
                for item in dist_dir.rglob("*"):
                    print(f"  {item.relative_to(dist_dir)}")
            return 1

    except subprocess.CalledProcessError as e:
        print(f"❌ Build failed with error code: {e.returncode}")
        if e.stdout:
            print("STDOUT:", e.stdout)
        if e.stderr:
            print("STDERR:", e.stderr)
        sys.exit(1)
    except Exception as e:
        print(f"❌ Unexpected error: {e}")
        import traceback

        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    sys.exit(main())
