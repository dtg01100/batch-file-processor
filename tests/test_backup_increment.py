import os
import shutil
import unittest
from unittest.mock import patch, MagicMock
import re
import backup_increment

class TestBackupIncrement(unittest.TestCase):
    @patch("backup_increment.os.path")
    @patch("backup_increment.os.mkdir")
    @patch("backup_increment.shutil.copy")
    @patch("backup_increment.utils.do_clear_old_files")
    def test_do_backup(self, mock_clear_old_files, mock_copy, mock_mkdir, mock_path):
        # Mock the input file and its properties
        input_file = "/path/to/input_file.txt"
        mock_path.abspath.return_value = input_file
        mock_path.dirname.return_value = "/path/to"
        mock_path.join.side_effect = lambda *args: "/".join(str(arg) for arg in args)
        mock_path.exists.side_effect = lambda path: path != "/path/to/backups"
        mock_path.isdir.return_value = False
        mock_path.basename.return_value = "input_file.txt"
        
        # Call the function
        backup_path = backup_increment.do_backup(input_file)

        # Assertions
        mock_mkdir.assert_called_once_with("/path/to/backups")
        mock_copy.assert_called_once_with(input_file, backup_path)
        mock_clear_old_files.assert_called_once_with("/path/to/backups", 50)
        # Validate backup_path using regex to match the expected format
        pattern = r"^/path/to/backups/input_file.txt.bak-.*"
        self.assertRegex(backup_path, pattern)

if __name__ == "__main__":
    unittest.main()
