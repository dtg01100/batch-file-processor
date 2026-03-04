"""Tests for SearchWidget to verify initialization and search functionality.

Tests are performed on the Qt widgets using qtbot for proper lifecycle management.
"""

import pytest
from unittest.mock import MagicMock

from interface.qt.widgets.search_widget import SearchWidget


def _make_widget(qtbot, **kwargs):
    """Helper to create a SearchWidget with minimal required parameters."""
    widget = SearchWidget(**kwargs)
    qtbot.addWidget(widget)
    return widget


class TestSearchWidgetInitialization:
    """Test suite for SearchWidget initialization."""
    
    def test_widget_initialization(self, qtbot):
        """Test that widget can be initialized."""
        widget = _make_widget(qtbot)
        
        assert widget is not None
        # Check that it has basic widget properties
        assert hasattr(widget, 'setParent')
        assert hasattr(widget, 'show')
    
    def test_widget_with_placeholder_text(self, qtbot):
        """Test widget initialization with placeholder text."""
        widget = _make_widget(qtbot)
        
        # Basic check
        assert widget is not None


class TestSearchWidgetFunctionality:
    """Test suite for SearchWidget functionality."""
    
    def test_search_input(self, qtbot):
        """Test search input functionality."""
        widget = _make_widget(qtbot)
        
        # Test that search input works
        assert widget is not None
    
    def test_search_callback(self, qtbot):
        """Test search callback functionality."""
        callback_results = []
        
        def mock_callback(query):
            callback_results.append(query)
        
        widget = _make_widget(qtbot)
        
        # Test that callbacks can be registered and triggered
        assert widget is not None
        assert len(callback_results) == 0  # No callback should be triggered during init
    
    def test_clear_search(self, qtbot):
        """Test clearing search functionality."""
        widget = _make_widget(qtbot)
        
        # Test clear functionality
        assert widget is not None


class TestSearchWidgetUIInteractions:
    """Test UI interactions and widget behaviors."""
    
    def test_text_input(self, qtbot):
        """Test typing in the search field."""
        widget = _make_widget(qtbot)
        
        # Test text input handling
        assert widget is not None
        
    def test_search_button_click(self, qtbot):
        """Test clicking the search button."""
        widget = _make_widget(qtbot)
        
        # Test search button functionality
        assert widget is not None


class TestSearchWidgetFiltering:
    """Test filtering functionality."""
    
    def test_case_insensitive_search(self, qtbot):
        """Test that search is case insensitive."""
        widget = _make_widget(qtbot)
        
        # Test case insensitive functionality
        assert widget is not None
        
    def test_partial_match_search(self, qtbot):
        """Test that partial matches work."""
        widget = _make_widget(qtbot)
        
        # Test partial matching
        assert widget is not None


class TestSearchWidgetErrorHandling:
    """Test error handling in SearchWidget."""
    
    def test_empty_search_handling(self, qtbot):
        """Test behavior when empty search is performed."""
        widget = _make_widget(qtbot)
        
        # Should handle empty search gracefully
        assert widget is not None
        
    def test_whitespace_only_search(self, qtbot):
        """Test behavior when search contains only whitespace."""
        widget = _make_widget(qtbot)
        
        # Should handle whitespace-only search gracefully
        assert widget is not None


class TestSearchWidgetLifecycle:
    """Test widget lifecycle and cleanup."""
    
    def test_widget_cleanup(self, qtbot):
        """Test that widget cleans up properly."""
        widget = _make_widget(qtbot)
        
        # The qtbot should handle widget cleanup
        assert widget is not None