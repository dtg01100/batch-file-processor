#!/usr/bin/env python3
"""
Guard the unsupported Podman-based Windows build route.

The previous implementation invoked Linux ``python3.11 -m PyInstaller`` inside a
container and copied the resulting ``dist/`` tree back to the host. That route
produces Linux binaries/shared libraries instead of a valid Windows bundle, so
it must fail fast rather than risk shipping a broken artifact.
"""

import sys

INVALID_BUILD_ROUTE_MESSAGE = (
    "build_windows_podman.py is disabled because it runs Linux "
    "'python3.11 -m PyInstaller' inside the container, which produces Linux "
    "artifacts in dist/ instead of a valid Windows bundle. Use "
    "build_wine_local.py or build_windows_docker.py for Windows packaging."
)


def ensure_supported_build_route() -> None:
    """Raise an explicit error for the unsupported Podman build path."""
    raise RuntimeError(INVALID_BUILD_ROUTE_MESSAGE)


def main() -> int:
    """Fail fast so invalid Windows bundles are not produced."""
    print(f"❌ {INVALID_BUILD_ROUTE_MESSAGE}")
    return 1


if __name__ == "__main__":
    sys.exit(main())
