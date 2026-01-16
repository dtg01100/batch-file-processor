#!/usr/bin/env python3
"""
Test runner to execute remote file system tests directly
"""

import sys
import os
sys.path.insert(0, os.path.abspath(os.path.dirname(os.path.dirname(__file__))))

from tests.unit.test_remote_fs import (
    test_local_file_system_initialization,
    test_local_file_system_operations,
    test_factory_create_local,
    test_directory_operations,
    test_upload_download_file,
    test_file_hash,
    test_directory_recursive_operations
)

def run_tests():
    """Run all tests and report results"""
    tests = [
        ("Local File System Initialization", test_local_file_system_initialization),
        ("Local File System Operations", test_local_file_system_operations),
        ("Factory Create Local", test_factory_create_local),
        ("Directory Operations", test_directory_operations),
        ("Upload/Download File", test_upload_download_file),
        ("File Hash Calculation", test_file_hash),
        ("Directory Recursive Operations", test_directory_recursive_operations)
    ]
    
    passed = 0
    failed = 0
    
    print("Running remote file system tests...")
    print("=" * 60)
    
    for test_name, test_func in tests:
        try:
            print(f"Running: {test_name}...", end="")
            test_func()
            print(" PASSED")
            passed += 1
        except Exception as e:
            print(f" FAILED")
            print(f"  Error: {e}")
            import traceback
            print(f"  Stack trace: {traceback.format_exc()}")
            failed += 1
    
    print("=" * 60)
    print(f"\nTest Results:")
    print(f"  Passed: {passed}")
    print(f"  Failed: {failed}")
    print(f"  Total: {passed + failed}")
    
    if failed == 0:
        print("\n✅ All tests passed!")
        return 0
    else:
        print("\n❌ Some tests failed!")
        return 1


if __name__ == "__main__":
    try:
        from backend.remote_fs.smb import SMB_AVAILABLE
        from backend.remote_fs.sftp import SFTP_AVAILABLE
        print(f"SMB Support: {'Available' if SMB_AVAILABLE else 'Not available'}")
        print(f"SFTP Support: {'Available' if SFTP_AVAILABLE else 'Not available'}")
        print()
    except Exception as e:
        print(f"Warning: Could not check optional dependencies: {e}")
        print()
    
    exit_code = run_tests()
    sys.exit(exit_code)
