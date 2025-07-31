import unittest
from dialog import Dialog
from unittest.mock import MagicMock, patch
import pytest
try:
    from tkinter import Toplevel
    TKINTER_AVAILABLE = True
except (ImportError, AttributeError):
    TKINTER_AVAILABLE = False
import pytest

@pytest.fixture(autouse=True)
def mock_toplevel():
    if not TKINTER_AVAILABLE:
        pytest.skip("tkinter.Toplevel not available")
    try:
        with patch("tkinter.Toplevel", new=MagicMock()) as MockToplevel:
            yield MockToplevel
    except AttributeError:
        pytest.skip("tkinter.Toplevel not available (patch failed)")


@pytest.mark.skipif(not TKINTER_AVAILABLE, reason="tkinter.Toplevel not available")
class TestDialog(unittest.TestCase):
    def test_initialization(self):
        root = Toplevel()
        foldersnameinput = MagicMock()
        dialog = Dialog(root, foldersnameinput)
        self.assertIsNotNone(dialog)

if __name__ == '__main__':
    unittest.main()
