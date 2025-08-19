import os
import tempfile

from business_logic import db as bl_db

def test_init_and_get_connection(tmp_path):
    # Use a temporary file path for a persistent sqlite DB file
    db_file = tmp_path / "test_folders.db"
    db_path = str(db_file)

    # Should not raise
    bl_db.init_db(db_path)

    conn = bl_db.get_connection()
    # basic assertions about the returned object
    assert conn is not None
    # Verify the version table exists and contains a row (init_db inserts one)
    version_table = conn["version"]
    row = version_table.find_one(id=1)
    assert row is not None

    # Cleanup
    bl_db.close()
    if os.path.exists(db_path):
        os.remove(db_path)