#!/usr/bin/env python3
"""Simple test script to verify imports only."""

import sys
import os

# Add project root to sys.path
_script_dir = os.path.dirname(os.path.abspath(__file__))
if _script_dir not in sys.path:
    sys.path.insert(0, _script_dir)

print("=== Import Test ===")
print(f"Python executable: {sys.executable}")
print(f"sys.path[0]: {sys.path[0]}")
print()

# Test 1: Check if we can import from interface package
try:
    print("✓ interface package imported successfully")
except Exception as e:
    print(f"✗ Failed to import interface: {e}")

# Test 2: Check if we can import interface.qt module
try:
    print("✓ interface.qt module imported successfully")
except Exception as e:
    print(f"✗ Failed to import interface.qt: {e}")

# Test 3: Check if we can import interface.qt.app module
try:
    print("✓ interface.qt.app module imported successfully")
except Exception as e:
    print(f"✗ Failed to import interface.qt.app: {e}")
    import traceback
    print(f"Stack trace: {traceback.format_exc()}")

print()
print("=== All tests completed ===")