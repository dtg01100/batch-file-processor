#!/bin/bash
# Build Windows executable using batonogov/pyinstaller-windows container

cd "$(dirname "$0")"

# Clean old dist to force rebuild
rm -rf dist/
mkdir -p dist

echo "Building Windows executable..."
docker run --rm \
  --volume "$(pwd):/src/" \
  docker.io/batonogov/pyinstaller-windows:v4.0.1 \
  pyinstaller --clean -y main_interface.spec

echo ""
echo "Build complete. Output in dist/"
ls -la dist/