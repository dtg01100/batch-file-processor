#!/usr/bin/env python3
"""
Windows build script that creates a Docker image with all source files
and builds the Windows executable without relying on volume mounts.
"""

import shutil
import subprocess
import sys
from pathlib import Path

from build_wine_local import (
    WINDOWS_EXECUTABLE_NAME,
    format_bundle_validation_errors,
    validate_windows_bundle,
)


def build_dockerfile_content() -> str:
    """Return the Dockerfile used for the Docker-based Windows build."""
    return """
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
"""


def _print_dist_contents(dist_dir: Path) -> None:
    """Print the extracted dist tree for debugging."""
    if dist_dir.exists():
        print("Contents of dist directory:")
        for item in dist_dir.rglob("*"):
            print(f"  {item}")


def _copy_dist_from_container(project_root: Path) -> None:
    """Copy /src/dist from the temporary image container."""
    container_id = subprocess.check_output(
        ["sudo", "docker", "create", "batch-file-processor-windows-build"],
        cwd=project_root,
        text=True,
    ).strip()

    try:
        subprocess.run(
            [
                "sudo",
                "docker",
                "cp",
                f"{container_id}:/src/dist",
                str(project_root),
            ],
            cwd=project_root,
            check=True,
        )
    finally:
        subprocess.run(
            ["sudo", "docker", "rm", container_id], cwd=project_root, check=False
        )


def _validate_extracted_bundle(dist_dir: Path) -> int:
    """Validate the extracted Windows executable."""
    exe_path = dist_dir / WINDOWS_EXECUTABLE_NAME
    issues = validate_windows_bundle(exe_path)

    if issues:
        print("❌ Build completed but executable validation failed")
        print(format_bundle_validation_errors(issues))
        _print_dist_contents(dist_dir)
        return 1

    if not exe_path.exists():
        print("❌ Build completed but executable not found")
        _print_dist_contents(dist_dir)
        return 1

    print("✅ Windows build completed successfully!")
    print(f"Executable location: {exe_path}")
    return 0


def main():
    project_root = Path(__file__).parent.absolute()
    dist_dir = project_root / "dist"
    dockerfile_path = project_root / "Dockerfile.windows.build"

    # Clean previous builds
    if dist_dir.exists():
        shutil.rmtree(dist_dir)

    print("Creating Dockerfile for Windows build...")
    with open(dockerfile_path, "w", encoding="utf-8") as f:
        f.write(build_dockerfile_content())

    try:
        print("Building Docker image...")
        # Build the Docker image
        subprocess.run(
            [
                "sudo",
                "docker",
                "build",
                "-f",
                "Dockerfile.windows.build",
                "-t",
                "batch-file-processor-windows-build",
                ".",
            ],
            cwd=project_root,
            check=True,
        )

        print("Running build container...")
        # Run the container to build the executable
        subprocess.run(
            ["sudo", "docker", "run", "--rm", "batch-file-processor-windows-build"],
            cwd=project_root,
            check=True,
        )

        print("Extracting built executable...")
        _copy_dist_from_container(project_root)

        return _validate_extracted_bundle(dist_dir)

    except subprocess.CalledProcessError as e:
        print(f"❌ Build failed with error: {e}")
        return 1
    except Exception as e:
        print(f"❌ Unexpected error: {e}")
        return 1
    finally:
        if dockerfile_path.exists():
            dockerfile_path.unlink()


if __name__ == "__main__":
    sys.exit(main())
