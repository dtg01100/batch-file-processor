"""Shared fixtures and configuration for all unit tests."""

import os

# Ensure Qt tests run in offscreen mode (no visible windows).
os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
