"""Batch File Sender - Qt Entry Point.

This module delegates to main_interface for consistency.
"""

import os
import sys

_script_dir = os.path.dirname(os.path.abspath(__file__))
if _script_dir not in sys.path:
    sys.path.insert(0, _script_dir)

from main_interface import main

if __name__ == "__main__":
    main()
