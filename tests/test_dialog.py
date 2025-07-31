import unittest
from dialog import Dialog
from unittest.mock import MagicMock, patch
from tkinter import Toplevel
import pytest
@pytest.fixture(autouse=True)
def mock_toplevel():
    with patch("tkinter.Toplevel", new=MagicMock()) as MockToplevel:
        yield MockToplevel

@unittest.skip("Skipping tests for dialog module")
class TestDialog(unittest.TestCase):
    def test_initialization(self):
        root = Toplevel()
        foldersnameinput = MagicMock()
        dialog = Dialog(root, foldersnameinput)
        self.assertIsNotNone(dialog)

if __name__ == '__main__':
    unittest.main()
