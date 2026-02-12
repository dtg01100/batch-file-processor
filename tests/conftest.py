"""Pytest configuration for the test suite."""

import sys
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

# Add the project root to the Python path FIRST, before any other imports
# This ensures the dispatch package is found correctly
project_root = Path(__file__).parent.parent.resolve()
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))


# ============================================================================
# Tkinter Mock Fixtures for Headless Testing
# ============================================================================

@pytest.fixture
def mock_tk_root():
    """Create a mock tkinter root window for headless testing."""
    root = MagicMock()
    root.after = MagicMock(return_value=1)  # Return an ID for after() calls
    root.after_cancel = MagicMock()
    root.winfo_rootx = MagicMock(return_value=100)
    root.winfo_rooty = MagicMock(return_value=100)
    root.bbox = MagicMock(return_value=(0, 0, 50, 20))
    return root


@pytest.fixture
def mock_tk_widget():
    """Create a mock tkinter widget for testing callbacks."""
    widget = MagicMock()
    widget.bind = MagicMock()
    widget.unbind = MagicMock()
    widget.cget = MagicMock(return_value='normal')
    widget.focus_force = MagicMock()
    widget.selection_present = MagicMock(return_value=True)
    widget.selection_range = MagicMock()
    widget.icursor = MagicMock()
    widget.event_generate = MagicMock()
    widget.selection_get = MagicMock(return_value='clipboard text')
    widget.after = MagicMock(return_value=1)
    widget.after_cancel = MagicMock()
    widget.winfo_rootx = MagicMock(return_value=100)
    widget.winfo_rooty = MagicMock(return_value=100)
    widget.winfo_reqwidth = MagicMock(return_value=200)
    widget.winfo_reqheight = MagicMock(return_value=300)
    widget.winfo_width = MagicMock(return_value=200)
    widget.bbox = MagicMock(return_value=(0, 0, 50, 20))
    widget.pack = MagicMock()
    widget.config = MagicMock()
    widget.configure = MagicMock()
    widget.destroy = MagicMock()
    return widget


@pytest.fixture
def mock_event():
    """Create a mock event object for testing event handlers."""
    event = MagicMock()
    event.x = 10
    event.y = 20
    event.x_root = 100
    event.y_root = 200
    event.widget = MagicMock()
    event.num = 4  # Button 4 for scroll up on Linux
    event.delta = 120  # Scroll delta for Windows
    return event


@pytest.fixture
def mock_event_none_coords():
    """Create a mock event with None coordinates for edge case testing."""
    event = MagicMock()
    event.x = None
    event.y = None
    event.x_root = None
    event.y_root = None
    event.widget = MagicMock()
    event.num = 4
    event.delta = 120
    return event


@pytest.fixture
def mock_menu():
    """Create a mock tkinter Menu widget."""
    menu = MagicMock()
    menu.add_command = MagicMock()
    menu.add_separator = MagicMock()
    menu.post = MagicMock()
    menu.destroy = MagicMock()
    return menu


@pytest.fixture
def mock_canvas():
    """Create a mock tkinter Canvas widget."""
    canvas = MagicMock()
    canvas.pack = MagicMock()
    canvas.config = MagicMock()
    canvas.configure = MagicMock()
    canvas.xview_moveto = MagicMock()
    canvas.yview_moveto = MagicMock()
    canvas.yview = MagicMock()
    canvas.create_window = MagicMock(return_value='interior_id')
    canvas.itemconfigure = MagicMock()
    canvas.winfo_width = MagicMock(return_value=200)
    canvas.bind = MagicMock()
    canvas.unbind = MagicMock()
    canvas.bind_all = MagicMock()
    canvas.unbind_all = MagicMock()
    return canvas


@pytest.fixture
def mock_scrollbar():
    """Create a mock tkinter Scrollbar widget."""
    scrollbar = MagicMock()
    scrollbar.pack = MagicMock()
    scrollbar.config = MagicMock()
    scrollbar.set = MagicMock()
    scrollbar.yview = MagicMock()
    scrollbar.bind = MagicMock()
    scrollbar.unbind = MagicMock()
    scrollbar.bind_all = MagicMock()
    scrollbar.unbind_all = MagicMock()
    return scrollbar


@pytest.fixture
def mock_toplevel():
    """Create a mock tkinter Toplevel widget."""
    toplevel = MagicMock()
    toplevel.wm_overrideredirect = MagicMock()
    toplevel.wm_geometry = MagicMock()
    toplevel.destroy = MagicMock()
    return toplevel


@pytest.fixture
def mock_tkinter_module(mock_menu, mock_toplevel):
    """Mock the tkinter module for headless testing of widgets."""
    with patch('tkinter.Tk') as mock_tk, \
         patch('tkinter.Menu') as mock_menu_cls, \
         patch('tkinter.Toplevel') as mock_toplevel_cls, \
         patch('tkinter.Frame') as mock_frame_cls, \
         patch('tkinter.Canvas') as mock_canvas_cls, \
         patch('tkinter.Label') as mock_label_cls, \
         patch('tkinter.ttk.Frame') as mock_ttk_frame, \
         patch('tkinter.ttk.Scrollbar') as mock_ttk_scrollbar:
        
        mock_menu_cls.return_value = mock_menu
        mock_toplevel_cls.return_value = mock_toplevel
        
        yield {
            'Tk': mock_tk,
            'Menu': mock_menu_cls,
            'Toplevel': mock_toplevel_cls,
            'Frame': mock_frame_cls,
            'Canvas': mock_canvas_cls,
            'Label': mock_label_cls,
            'ttk.Frame': mock_ttk_frame,
            'ttk.Scrollbar': mock_ttk_scrollbar,
        }
