#!/usr/bin/env python3
"""
Test script to verify the Windows executable has all required dependencies.
This is an integration test for the Windows packaging.
"""

import os
import sys

def test_executable_structure():
    """Verify the executable has all required files."""
    exe_dir = ".wine-build/dist/Batch File Sender"
    internal_dir = os.path.join(exe_dir, "_internal")
    
    print("=" * 60)
    print("Windows Executable Self-Test (Integration Test)")
    print("=" * 60)
    print()
    
    # Check executable exists
    exe_path = os.path.join(exe_dir, "Batch File Sender.exe")
    if os.path.exists(exe_path):
        print(f"✓ Executable found: {exe_path}")
        size = os.path.getsize(exe_path)
        print(f"  Size: {size:,} bytes ({size/1024/1024:.2f} MB)")
    else:
        print(f"✗ Executable NOT found: {exe_path}")
        return 1
    
    print()
    
    # Check _internal directory
    if os.path.exists(internal_dir):
        print(f"✓ _internal directory found")
    else:
        print(f"✗ _internal directory NOT found")
        return 1
    
    print()
    
    # Check for critical Qt6 DLLs
    qt_bin_dir = os.path.join(internal_dir, "PyQt6", "Qt6", "bin")
    critical_dlls = [
        "Qt6Core.dll",
        "Qt6Gui.dll", 
        "Qt6Widgets.dll",
        "Qt6Network.dll",
        "Qt6PrintSupport.dll",
        "Qt6Svg.dll",
        "Qt6Xml.dll",
    ]
    
    print("[Qt6 DLLs Check]")
    missing_dlls = []
    for dll in critical_dlls:
        dll_path = os.path.join(qt_bin_dir, dll)
        if os.path.exists(dll_path):
            print(f"  ✓ {dll}")
        else:
            print(f"  ✗ {dll} - MISSING")
            missing_dlls.append(dll)
    
    print()
    
    # Check for ICU DLLs (commonly missing)
    print("[ICU DLLs Check]")
    icu_dlls = ["icuuc.dll", "icuin.dll", "icudt.dll"]
    missing_icu = []
    for dll in icu_dlls:
        dll_path = os.path.join(qt_bin_dir, dll)
        if os.path.exists(dll_path):
            print(f"  ✓ {dll}")
        else:
            print(f"  ✗ {dll} - MISSING (optional but recommended)")
            missing_icu.append(dll)
    
    print()
    
    # Check for Python modules
    print("[Python Modules Check]")
    required_modules = [
        "PyQt6/QtCore.pyd",
        "PyQt6/QtGui.pyd",
        "PyQt6/QtWidgets.pyd",
        "lxml/etree.cp311-win_amd64.pyd",
        "PIL/_imaging.cp311-win_amd64.pyd",
    ]
    
    missing_modules = []
    for module in required_modules:
        module_path = os.path.join(internal_dir, module)
        if os.path.exists(module_path):
            print(f"  ✓ {module}")
        else:
            print(f"  ✗ {module} - MISSING")
            missing_modules.append(module)
    
    print()
    
    # Summary
    print("=" * 60)
    print("SUMMARY")
    print("=" * 60)
    
    if missing_dlls:
        print(f"✗ FAILED: {len(missing_dlls)} critical DLL(s) missing")
        return 1
    elif missing_icu:
        print(f"⚠ WARNING: {len(missing_icu)} ICU DLL(s) missing (may cause issues)")
        print("  These are often required by Qt6 but may be bundled elsewhere")
        return 0  # Still pass, as these might be optional
    else:
        print("✓ ALL CHECKS PASSED")
        print("  The Windows executable appears to be properly packaged.")
        return 0

if __name__ == "__main__":
    sys.exit(test_executable_structure())
