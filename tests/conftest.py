"""Pytest configuration for the test suite."""

import sys
from pathlib import Path
from unittest.mock import MagicMock

import pytest

project_root = Path(__file__).parent.parent.resolve()
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))


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
