# Windows Build Troubleshooting Guide

## Issue Summary

The Windows build process using Docker (`buildwin.sh` and `buildwin_test.sh`) fails when run inside a **devcontainer** environment due to Docker-in-Docker volume mounting limitations.

### Error Symptoms
- `Spec file "/src/main_interface.spec" not found!`
- Volume mounts from host filesystem to container fail silently
- Files appear to be missing in the container despite existing on the host

### Root Cause
When running Docker inside a devcontainer:
1. The `/workspaces` directory is often mounted as read-only
2. Docker volume mounting from the host filesystem to containers has permission/path issues
3. The nested container environment creates filesystem isolation problems

## Solutions

### ✅ Solution 1: Use Linux Build (Recommended for Development)
The Linux build works perfectly in all environments:

```bash
./build_local.sh --build-only
# Test the executable
./dist/Batch\ File\ Sender/Batch\ File\ Sender --self-test
```

### ✅ Solution 2: Build Windows Executable on Host System
Run the build scripts directly on your host machine (outside of devcontainer):

```bash
# On your host system (Linux, macOS, or Windows with WSL2)
git clone https://github.com/dtg01100/batch-file-processor.git
cd batch-file-processor
./buildwin.sh
```

### ✅ Solution 3: Use GitHub Actions/CI
Set up automated Windows builds using GitHub Actions or other CI/CD platforms that don't have devcontainer limitations.

### ⚠️ Solution 4: Manual Docker Build (Advanced)
If you must build in the devcontainer, use this manual approach:

```bash
# Create a custom Dockerfile
cat > Dockerfile.windows << 'EOF'
FROM docker.io/batonogov/pyinstaller-windows:v4.0.1
COPY . /src/
WORKDIR /src
ENV SPECFILE=/src/main_interface.spec
CMD ["pyinstaller", "/src/main_interface.spec"]
EOF

# Build the image (this will take a long time - ~1.5GB transfer)
sudo docker build -f Dockerfile.windows -t batch-win-build .

# Extract the dist directory
sudo docker create --name win-build-container batch-win-build
sudo docker cp win-build-container:/src/dist ./dist
sudo docker rm win-build-container
```

**Note**: This approach is slow and may still have issues due to the large workspace size.

## Current Status

- **Linux Build**: ✅ Working perfectly
- **Windows Build in Devcontainer**: ❌ Not working due to Docker-in-Docker limitations
- **Windows Build on Host**: ✅ Should work normally

## Recommendation

For development and testing, use the Linux build. For production Windows deployments, build on a host system or use CI/CD pipelines.

## Verification Steps

1. **Test Linux build**:
   ```bash
   ./build_local.sh --build-only
   ./dist/Batch\ File\ Sender/Batch\ File\ Sender --self-test
   ```

2. **If you need Windows executable**, build on host system or use CI/CD.

3. **Avoid running Windows build scripts inside devcontainers** until Docker-in-Docker volume mounting issues are resolved.

---

*Last updated: February 27, 2026*