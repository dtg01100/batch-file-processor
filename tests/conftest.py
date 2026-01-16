import os
import sys
from pathlib import Path

project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

if "BATCH_PROCESSOR_DB_ENABLED" not in os.environ:
    os.environ["BATCH_PROCESSOR_DB_ENABLED"] = "false"
