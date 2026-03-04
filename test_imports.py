#!/usr/bin/env python3
"""Test script to verify the application can be imported and run."""

import sys
import os

# Add project root to sys.path
_script_dir = os.path.dirname(os.path.abspath(__file__))
if _script_dir not in sys.path:
    sys.path.insert(0, _script_dir)

print("Test 1: sys.path includes project root")
print(f"  sys.path[0]: {sys.path[0]}")
print(f"  Script directory: {_script_dir}")

print("\nTest 2: Checking if main_interface module can be imported")
import main_interface
print("✓ main_interface module imported successfully")

print("\nTest 3: Checking if interface.qt.app module is accessible")
from interface.qt.app import QtBatchFileSenderApp
print("✓ QtBatchFileSenderApp class imported successfully")

print("\nTest 4: Creating an instance of the application")
try:
    app = QtBatchFileSenderApp(
        appname="Test App",
        version="Test Version",
        database_version="1"
    )
    print("✓ QtBatchFileSenderApp instance created successfully")
    
    print("\nTest 5: Checking if main() function exists")
    if hasattr(main_interface, 'main') and callable(main_interface.main):
        print("✓ main() function is callable")
    else:
        print("✗ main() function not found or not callable")
        
except Exception as e:
    print(f"✗ Error creating QtBatchFileSenderApp instance: {e}")
    import traceback
    print(f"\nStack trace: {traceback.format_exc()}")

print("\n\nAll tests completed!")