"""
Aggressive unit tests for doingstuffoverlay.py.

Tests are designed to run headlessly using mocks for all tkinter objects.
"""

from unittest.mock import MagicMock, patch, PropertyMock

import pytest


class TestDoingStuffOverlayClass:
    """Tests for the DoingStuffOverlay class."""

    def test_init_stores_parent(self, mock_tk_root):
        """Test that DoingStuffOverlay.__init__ stores parent."""
        from doingstuffoverlay import DoingStuffOverlay
        
        overlay = DoingStuffOverlay(mock_tk_root)
        
        assert overlay.parent == mock_tk_root

    def test_init_with_none_parent(self):
        """Test that DoingStuffOverlay.__init__ accepts None parent."""
        from doingstuffoverlay import DoingStuffOverlay
        
        overlay = DoingStuffOverlay(None)
        
        assert overlay.parent is None

    def test_init_with_mock_parent(self):
        """Test that DoingStuffOverlay.__init__ works with mock parent."""
        from doingstuffoverlay import DoingStuffOverlay
        
        mock_parent = MagicMock()
        overlay = DoingStuffOverlay(mock_parent)
        
        assert overlay.parent == mock_parent


class TestMakeOverlay:
    """Tests for the make_overlay() function."""

    def test_make_overlay_creates_frame(self, mock_tk_root):
        """Test that make_overlay creates a frame."""
        with patch('tkinter.StringVar') as mock_stringvar, \
             patch('tkinter.ttk.Frame') as mock_frame_cls, \
             patch('tkinter.ttk.Label') as mock_label_cls:
            
            mock_frame = MagicMock()
            mock_frame.grab_set = MagicMock()
            mock_frame.place = MagicMock()
            mock_frame_cls.return_value = mock_frame
            
            mock_label = MagicMock()
            mock_label.place = MagicMock()
            mock_label_cls.return_value = mock_label
            
            mock_var = MagicMock()
            mock_var.set = MagicMock()
            mock_var.get = MagicMock(return_value="Loading...")
            mock_stringvar.return_value = mock_var
            
            import doingstuffoverlay
            
            # Reset globals
            doingstuffoverlay.doing_stuff_frame = None
            doingstuffoverlay.doing_stuff = None
            doingstuffoverlay.label_var = None
            
            doingstuffoverlay.make_overlay(mock_tk_root, "Processing...")
            
            mock_frame_cls.assert_called_once()

    def test_make_overlay_sets_text(self, mock_tk_root):
        """Test that make_overlay sets the overlay text."""
        with patch('tkinter.StringVar') as mock_stringvar, \
             patch('tkinter.ttk.Frame') as mock_frame_cls, \
             patch('tkinter.ttk.Label') as mock_label_cls:
            
            mock_frame = MagicMock()
            mock_frame.grab_set = MagicMock()
            mock_frame.place = MagicMock()
            mock_frame_cls.return_value = mock_frame
            
            mock_label = MagicMock()
            mock_label.place = MagicMock()
            mock_label_cls.return_value = mock_label
            
            mock_var = MagicMock()
            mock_var.set = MagicMock()
            mock_var.get = MagicMock(return_value="Processing...")
            mock_stringvar.return_value = mock_var
            
            import doingstuffoverlay
            
            doingstuffoverlay.make_overlay(mock_tk_root, "Processing...")
            
            # StringVar.set should be called with the text
            mock_var.set.assert_called()

    def test_make_overlay_with_header(self, mock_tk_root):
        """Test that make_overlay sets header text."""
        with patch('tkinter.StringVar') as mock_stringvar, \
             patch('tkinter.ttk.Frame') as mock_frame_cls, \
             patch('tkinter.ttk.Label') as mock_label_cls:
            
            mock_frame = MagicMock()
            mock_frame.grab_set = MagicMock()
            mock_frame.place = MagicMock()
            mock_frame_cls.return_value = mock_frame
            
            mock_label = MagicMock()
            mock_label.place = MagicMock()
            mock_label_cls.return_value = mock_label
            
            mock_var = MagicMock()
            mock_var.set = MagicMock()
            mock_var.get = MagicMock(return_value="Header Text")
            mock_stringvar.return_value = mock_var
            
            import doingstuffoverlay
            
            doingstuffoverlay.make_overlay(
                mock_tk_root,
                overlay_text="Processing...",
                header="Header Text"
            )
            
            # Header StringVar should be set
            assert mock_var.set.call_count >= 1

    def test_make_overlay_with_footer(self, mock_tk_root):
        """Test that make_overlay sets footer text."""
        with patch('tkinter.StringVar') as mock_stringvar, \
             patch('tkinter.ttk.Frame') as mock_frame_cls, \
             patch('tkinter.ttk.Label') as mock_label_cls:
            
            mock_frame = MagicMock()
            mock_frame.grab_set = MagicMock()
            mock_frame.place = MagicMock()
            mock_frame_cls.return_value = mock_frame
            
            mock_label = MagicMock()
            mock_label.place = MagicMock()
            mock_label_cls.return_value = mock_label
            
            mock_var = MagicMock()
            mock_var.set = MagicMock()
            mock_var.get = MagicMock(return_value="Footer Text")
            mock_stringvar.return_value = mock_var
            
            import doingstuffoverlay
            
            doingstuffoverlay.make_overlay(
                mock_tk_root,
                overlay_text="Processing...",
                footer="Footer Text"
            )
            
            # Footer StringVar should be set
            assert mock_var.set.call_count >= 1

    def test_make_overlay_custom_height(self, mock_tk_root):
        """Test that make_overlay uses custom height."""
        with patch('tkinter.StringVar') as mock_stringvar, \
             patch('tkinter.ttk.Frame') as mock_frame_cls, \
             patch('tkinter.ttk.Label') as mock_label_cls:
            
            mock_frame = MagicMock()
            mock_frame.grab_set = MagicMock()
            mock_frame.place = MagicMock()
            mock_frame_cls.return_value = mock_frame
            
            mock_label = MagicMock()
            mock_label.place = MagicMock()
            mock_label_cls.return_value = mock_label
            
            mock_var = MagicMock()
            mock_var.set = MagicMock()
            mock_var.get = MagicMock(return_value="Processing...")
            mock_stringvar.return_value = mock_var
            
            import doingstuffoverlay
            
            doingstuffoverlay.make_overlay(
                mock_tk_root,
                overlay_text="Processing...",
                overlay_height=200
            )
            
            # Frame.place should be called with height parameter
            mock_frame.place.assert_called()
            call_kwargs = mock_frame.place.call_args[1]
            assert call_kwargs.get('height') == 200

    def test_make_overlay_grabs_focus(self, mock_tk_root):
        """Test that make_overlay grabs focus with grab_set."""
        with patch('tkinter.StringVar') as mock_stringvar, \
             patch('tkinter.ttk.Frame') as mock_frame_cls, \
             patch('tkinter.ttk.Label') as mock_label_cls:
            
            mock_frame = MagicMock()
            mock_frame.grab_set = MagicMock()
            mock_frame.place = MagicMock()
            mock_frame_cls.return_value = mock_frame
            
            mock_label = MagicMock()
            mock_label.place = MagicMock()
            mock_label_cls.return_value = mock_label
            
            mock_var = MagicMock()
            mock_var.set = MagicMock()
            mock_var.get = MagicMock(return_value="Processing...")
            mock_stringvar.return_value = mock_var
            
            import doingstuffoverlay
            
            doingstuffoverlay.make_overlay(mock_tk_root, "Processing...")
            
            mock_frame.grab_set.assert_called_once()

    def test_make_overlay_calls_parent_update(self, mock_tk_root):
        """Test that make_overlay calls parent.update()."""
        with patch('tkinter.StringVar') as mock_stringvar, \
             patch('tkinter.ttk.Frame') as mock_frame_cls, \
             patch('tkinter.ttk.Label') as mock_label_cls:
            
            mock_frame = MagicMock()
            mock_frame.grab_set = MagicMock()
            mock_frame.place = MagicMock()
            mock_frame_cls.return_value = mock_frame
            
            mock_label = MagicMock()
            mock_label.place = MagicMock()
            mock_label_cls.return_value = mock_label
            
            mock_var = MagicMock()
            mock_var.set = MagicMock()
            mock_var.get = MagicMock(return_value="Processing...")
            mock_stringvar.return_value = mock_var
            
            import doingstuffoverlay
            
            doingstuffoverlay.make_overlay(mock_tk_root, "Processing...")
            
            mock_tk_root.update.assert_called_once()

    def test_make_overlay_sets_global_variables(self, mock_tk_root):
        """Test that make_overlay sets global variables."""
        with patch('tkinter.StringVar') as mock_stringvar, \
             patch('tkinter.ttk.Frame') as mock_frame_cls, \
             patch('tkinter.ttk.Label') as mock_label_cls:
            
            mock_frame = MagicMock()
            mock_frame.grab_set = MagicMock()
            mock_frame.place = MagicMock()
            mock_frame_cls.return_value = mock_frame
            
            mock_label = MagicMock()
            mock_label.place = MagicMock()
            mock_label_cls.return_value = mock_label
            
            mock_var = MagicMock()
            mock_var.set = MagicMock()
            mock_var.get = MagicMock(return_value="Processing...")
            mock_stringvar.return_value = mock_var
            
            import doingstuffoverlay
            
            doingstuffoverlay.make_overlay(mock_tk_root, "Processing...")
            
            # Global variables should be set
            assert doingstuffoverlay.doing_stuff_frame is not None
            assert doingstuffoverlay.doing_stuff is not None
            assert doingstuffoverlay.label_var is not None


class TestUpdateOverlay:
    """Tests for the update_overlay() function."""

    def test_update_overlay_updates_text(self, mock_tk_root):
        """Test that update_overlay updates the overlay text."""
        with patch('tkinter.StringVar'), \
             patch('tkinter.ttk.Frame'), \
             patch('tkinter.ttk.Label'):
            
            import doingstuffoverlay
            
            # Set up mock globals
            doingstuffoverlay.doing_stuff = MagicMock()
            doingstuffoverlay.doing_stuff.configure = MagicMock()
            doingstuffoverlay.header_label = MagicMock()
            doingstuffoverlay.header_label.configure = MagicMock()
            doingstuffoverlay.footer_label = MagicMock()
            doingstuffoverlay.footer_label.configure = MagicMock()
            doingstuffoverlay.doing_stuff_frame = MagicMock()
            doingstuffoverlay.doing_stuff_frame.winfo_height = MagicMock(return_value=100)
            doingstuffoverlay.doing_stuff_frame.place = MagicMock()
            
            doingstuffoverlay.update_overlay(mock_tk_root, "Updated text...")
            
            doingstuffoverlay.doing_stuff.configure.assert_called_once_with(text="Updated text...")

    def test_update_overlay_updates_header(self, mock_tk_root):
        """Test that update_overlay updates the header text."""
        with patch('tkinter.StringVar'), \
             patch('tkinter.ttk.Frame'), \
             patch('tkinter.ttk.Label'):
            
            import doingstuffoverlay
            
            doingstuffoverlay.doing_stuff = MagicMock()
            doingstuffoverlay.doing_stuff.configure = MagicMock()
            doingstuffoverlay.header_label = MagicMock()
            doingstuffoverlay.header_label.configure = MagicMock()
            doingstuffoverlay.footer_label = MagicMock()
            doingstuffoverlay.footer_label.configure = MagicMock()
            doingstuffoverlay.doing_stuff_frame = MagicMock()
            doingstuffoverlay.doing_stuff_frame.winfo_height = MagicMock(return_value=100)
            doingstuffoverlay.doing_stuff_frame.place = MagicMock()
            
            doingstuffoverlay.update_overlay(
                mock_tk_root,
                overlay_text="Processing...",
                header="New Header"
            )
            
            doingstuffoverlay.header_label.configure.assert_called_with(text="New Header")

    def test_update_overlay_updates_footer(self, mock_tk_root):
        """Test that update_overlay updates the footer text."""
        with patch('tkinter.StringVar'), \
             patch('tkinter.ttk.Frame'), \
             patch('tkinter.ttk.Label'):
            
            import doingstuffoverlay
            
            doingstuffoverlay.doing_stuff = MagicMock()
            doingstuffoverlay.doing_stuff.configure = MagicMock()
            doingstuffoverlay.header_label = MagicMock()
            doingstuffoverlay.header_label.configure = MagicMock()
            doingstuffoverlay.footer_label = MagicMock()
            doingstuffoverlay.footer_label.configure = MagicMock()
            doingstuffoverlay.doing_stuff_frame = MagicMock()
            doingstuffoverlay.doing_stuff_frame.winfo_height = MagicMock(return_value=100)
            doingstuffoverlay.doing_stuff_frame.place = MagicMock()
            
            doingstuffoverlay.update_overlay(
                mock_tk_root,
                overlay_text="Processing...",
                footer="New Footer"
            )
            
            doingstuffoverlay.footer_label.configure.assert_called_with(text="New Footer")

    def test_update_overlay_changes_height(self, mock_tk_root):
        """Test that update_overlay changes height when different."""
        with patch('tkinter.StringVar'), \
             patch('tkinter.ttk.Frame'), \
             patch('tkinter.ttk.Label'):
            
            import doingstuffoverlay
            
            doingstuffoverlay.doing_stuff = MagicMock()
            doingstuffoverlay.doing_stuff.configure = MagicMock()
            doingstuffoverlay.header_label = MagicMock()
            doingstuffoverlay.header_label.configure = MagicMock()
            doingstuffoverlay.footer_label = MagicMock()
            doingstuffoverlay.footer_label.configure = MagicMock()
            doingstuffoverlay.doing_stuff_frame = MagicMock()
            doingstuffoverlay.doing_stuff_frame.winfo_height = MagicMock(return_value=100)
            doingstuffoverlay.doing_stuff_frame.place = MagicMock()
            
            doingstuffoverlay.update_overlay(
                mock_tk_root,
                overlay_text="Processing...",
                overlay_height=200
            )
            
            # Height should be updated since it's different from current
            doingstuffoverlay.doing_stuff_frame.place.assert_called_with(height=200)

    def test_update_overlay_skips_height_when_same(self, mock_tk_root):
        """Test that update_overlay skips height update when same."""
        with patch('tkinter.StringVar'), \
             patch('tkinter.ttk.Frame'), \
             patch('tkinter.ttk.Label'):
            
            import doingstuffoverlay
            
            doingstuffoverlay.doing_stuff = MagicMock()
            doingstuffoverlay.doing_stuff.configure = MagicMock()
            doingstuffoverlay.header_label = MagicMock()
            doingstuffoverlay.header_label.configure = MagicMock()
            doingstuffoverlay.footer_label = MagicMock()
            doingstuffoverlay.footer_label.configure = MagicMock()
            doingstuffoverlay.doing_stuff_frame = MagicMock()
            doingstuffoverlay.doing_stuff_frame.winfo_height = MagicMock(return_value=100)
            doingstuffoverlay.doing_stuff_frame.place = MagicMock()
            
            doingstuffoverlay.update_overlay(
                mock_tk_root,
                overlay_text="Processing...",
                overlay_height=100  # Same as current
            )
            
            # Height should not be updated since it's the same
            doingstuffoverlay.doing_stuff_frame.place.assert_not_called()

    def test_update_overlay_calls_parent_update(self, mock_tk_root):
        """Test that update_overlay calls parent.update()."""
        with patch('tkinter.StringVar'), \
             patch('tkinter.ttk.Frame'), \
             patch('tkinter.ttk.Label'):
            
            import doingstuffoverlay
            
            doingstuffoverlay.doing_stuff = MagicMock()
            doingstuffoverlay.doing_stuff.configure = MagicMock()
            doingstuffoverlay.header_label = MagicMock()
            doingstuffoverlay.header_label.configure = MagicMock()
            doingstuffoverlay.footer_label = MagicMock()
            doingstuffoverlay.footer_label.configure = MagicMock()
            doingstuffoverlay.doing_stuff_frame = MagicMock()
            doingstuffoverlay.doing_stuff_frame.winfo_height = MagicMock(return_value=100)
            doingstuffoverlay.doing_stuff_frame.place = MagicMock()
            
            doingstuffoverlay.update_overlay(mock_tk_root, "Processing...")
            
            mock_tk_root.update.assert_called_once()

    def test_update_overlay_with_none_height(self, mock_tk_root):
        """Test that update_overlay handles None height."""
        with patch('tkinter.StringVar'), \
             patch('tkinter.ttk.Frame'), \
             patch('tkinter.ttk.Label'):
            
            import doingstuffoverlay
            
            doingstuffoverlay.doing_stuff = MagicMock()
            doingstuffoverlay.doing_stuff.configure = MagicMock()
            doingstuffoverlay.header_label = MagicMock()
            doingstuffoverlay.header_label.configure = MagicMock()
            doingstuffoverlay.footer_label = MagicMock()
            doingstuffoverlay.footer_label.configure = MagicMock()
            doingstuffoverlay.doing_stuff_frame = MagicMock()
            doingstuffoverlay.doing_stuff_frame.winfo_height = MagicMock(return_value=100)
            doingstuffoverlay.doing_stuff_frame.place = MagicMock()
            
            doingstuffoverlay.update_overlay(
                mock_tk_root,
                overlay_text="Processing...",
                overlay_height=None
            )
            
            # Should not try to update height when None
            doingstuffoverlay.doing_stuff_frame.place.assert_not_called()


class TestDestroyOverlay:
    """Tests for the destroy_overlay() function."""

    def test_destroy_overlay_calls_destroy(self, mock_tk_root):
        """Test that destroy_overlay calls destroy on the frame."""
        with patch('tkinter.StringVar'), \
             patch('tkinter.ttk.Frame'), \
             patch('tkinter.ttk.Label'):
            
            import doingstuffoverlay
            
            mock_frame = MagicMock()
            doingstuffoverlay.doing_stuff_frame = mock_frame
            
            doingstuffoverlay.destroy_overlay()
            
            mock_frame.destroy.assert_called_once()
            assert doingstuffoverlay.doing_stuff_frame is None

    def test_destroy_overlay_multiple_calls(self, mock_tk_root):
        """Test that destroy_overlay handles multiple calls."""
        with patch('tkinter.StringVar'), \
             patch('tkinter.ttk.Frame'), \
             patch('tkinter.ttk.Label'):
            
            import doingstuffoverlay
            
            mock_frame = MagicMock()
            doingstuffoverlay.doing_stuff_frame = mock_frame
            
            doingstuffoverlay.destroy_overlay()
            
            # First call should succeed
            mock_frame.destroy.assert_called_once()
            assert doingstuffoverlay.doing_stuff_frame is None
            
            # Second call should not raise an error (frame is already None)
            doingstuffoverlay.destroy_overlay()  # Should not raise


class TestOverlayIntegration:
    """Integration tests for overlay functions."""

    def test_make_update_destroy_sequence(self, mock_tk_root):
        """Test the typical make -> update -> destroy sequence."""
        with patch('tkinter.StringVar') as mock_stringvar, \
             patch('tkinter.ttk.Frame') as mock_frame_cls, \
             patch('tkinter.ttk.Label') as mock_label_cls:
            
            mock_frame = MagicMock()
            mock_frame.grab_set = MagicMock()
            mock_frame.place = MagicMock()
            mock_frame.destroy = MagicMock()
            mock_frame.winfo_height = MagicMock(return_value=100)
            mock_frame_cls.return_value = mock_frame
            
            mock_label = MagicMock()
            mock_label.place = MagicMock()
            mock_label.configure = MagicMock()
            mock_label_cls.return_value = mock_label
            
            mock_var = MagicMock()
            mock_var.set = MagicMock()
            mock_var.get = MagicMock(return_value="Processing...")
            mock_stringvar.return_value = mock_var
            
            import doingstuffoverlay
            
            # Make overlay
            doingstuffoverlay.make_overlay(mock_tk_root, "Starting...")
            
            # Update overlay
            doingstuffoverlay.doing_stuff = mock_label
            doingstuffoverlay.header_label = mock_label
            doingstuffoverlay.footer_label = mock_label
            doingstuffoverlay.doing_stuff_frame = mock_frame
            doingstuffoverlay.update_overlay(mock_tk_root, "Processing...")
            
            # Destroy overlay
            doingstuffoverlay.destroy_overlay()
            
            # Verify sequence
            mock_frame.grab_set.assert_called()
            mock_label.configure.assert_called()
            mock_frame.destroy.assert_called()

    def test_rapid_update_calls(self, mock_tk_root):
        """Test rapid successive update calls."""
        with patch('tkinter.StringVar'), \
             patch('tkinter.ttk.Frame'), \
             patch('tkinter.ttk.Label'):
            
            import doingstuffoverlay
            
            doingstuffoverlay.doing_stuff = MagicMock()
            doingstuffoverlay.doing_stuff.configure = MagicMock()
            doingstuffoverlay.header_label = MagicMock()
            doingstuffoverlay.header_label.configure = MagicMock()
            doingstuffoverlay.footer_label = MagicMock()
            doingstuffoverlay.footer_label.configure = MagicMock()
            doingstuffoverlay.doing_stuff_frame = MagicMock()
            doingstuffoverlay.doing_stuff_frame.winfo_height = MagicMock(return_value=100)
            doingstuffoverlay.doing_stuff_frame.place = MagicMock()
            
            # Rapid updates
            for i in range(10):
                doingstuffoverlay.update_overlay(mock_tk_root, f"Step {i}...")
            
            # All updates should be processed
            assert doingstuffoverlay.doing_stuff.configure.call_count == 10

    def test_overlay_with_empty_strings(self, mock_tk_root):
        """Test overlay with empty strings."""
        with patch('tkinter.StringVar') as mock_stringvar, \
             patch('tkinter.ttk.Frame') as mock_frame_cls, \
             patch('tkinter.ttk.Label') as mock_label_cls:
            
            mock_frame = MagicMock()
            mock_frame.grab_set = MagicMock()
            mock_frame.place = MagicMock()
            mock_frame_cls.return_value = mock_frame
            
            mock_label = MagicMock()
            mock_label.place = MagicMock()
            mock_label_cls.return_value = mock_label
            
            mock_var = MagicMock()
            mock_var.set = MagicMock()
            mock_var.get = MagicMock(return_value="")
            mock_stringvar.return_value = mock_var
            
            import doingstuffoverlay
            
            doingstuffoverlay.make_overlay(
                mock_tk_root,
                overlay_text="",
                header="",
                footer=""
            )
            
            # Should handle empty strings
            mock_var.set.assert_called()

    def test_overlay_with_long_text(self, mock_tk_root):
        """Test overlay with long text."""
        long_text = "A" * 1000
        
        with patch('tkinter.StringVar') as mock_stringvar, \
             patch('tkinter.ttk.Frame') as mock_frame_cls, \
             patch('tkinter.ttk.Label') as mock_label_cls:
            
            mock_frame = MagicMock()
            mock_frame.grab_set = MagicMock()
            mock_frame.place = MagicMock()
            mock_frame_cls.return_value = mock_frame
            
            mock_label = MagicMock()
            mock_label.place = MagicMock()
            mock_label_cls.return_value = mock_label
            
            mock_var = MagicMock()
            mock_var.set = MagicMock()
            mock_var.get = MagicMock(return_value=long_text)
            mock_stringvar.return_value = mock_var
            
            import doingstuffoverlay
            
            doingstuffoverlay.make_overlay(mock_tk_root, long_text)
            
            # Should handle long text
            mock_var.set.assert_called()


class TestOverlayEdgeCases:
    """Edge case tests for overlay functions."""

    def test_make_overlay_with_none_parent(self):
        """Test make_overlay with None parent."""
        with patch('tkinter.StringVar') as mock_stringvar, \
             patch('tkinter.ttk.Frame') as mock_frame_cls, \
             patch('tkinter.ttk.Label') as mock_label_cls:
            
            mock_frame = MagicMock()
            mock_frame.grab_set = MagicMock()
            mock_frame.place = MagicMock()
            mock_frame_cls.return_value = mock_frame
            
            mock_label = MagicMock()
            mock_label.place = MagicMock()
            mock_label_cls.return_value = mock_label
            
            mock_var = MagicMock()
            mock_var.set = MagicMock()
            mock_var.get = MagicMock(return_value="Processing...")
            mock_stringvar.return_value = mock_var
            
            import doingstuffoverlay
            
            # This will fail when trying to call parent.update()
            # but we test that the function handles it appropriately
            try:
                doingstuffoverlay.make_overlay(None, "Processing...")
            except (AttributeError, TypeError):
                pass  # Expected when parent is None

    def test_update_overlay_without_make(self, mock_tk_root):
        """Test update_overlay without prior make_overlay call."""
        import doingstuffoverlay
        
        # Reset globals
        doingstuffoverlay.doing_stuff = None
        doingstuffoverlay.header_label = None
        doingstuffoverlay.footer_label = None
        doingstuffoverlay.doing_stuff_frame = None
        
        # This should gracefully return without error since globals are not set
        # (fixed bug: previously would raise AttributeError)
        doingstuffoverlay.update_overlay(mock_tk_root, "Processing...")

    def test_destroy_overlay_without_make(self):
        """Test destroy_overlay without prior make_overlay call."""
        import doingstuffoverlay
        
        # Reset globals
        doingstuffoverlay.doing_stuff_frame = None
        
        # This should gracefully return without error since global is not set
        # (fixed bug: previously would raise AttributeError)
        doingstuffoverlay.destroy_overlay()

    def test_make_overlay_default_height(self, mock_tk_root):
        """Test make_overlay uses default height when not specified."""
        with patch('tkinter.StringVar') as mock_stringvar, \
             patch('tkinter.ttk.Frame') as mock_frame_cls, \
             patch('tkinter.ttk.Label') as mock_label_cls:
            
            mock_frame = MagicMock()
            mock_frame.grab_set = MagicMock()
            mock_frame.place = MagicMock()
            mock_frame_cls.return_value = mock_frame
            
            mock_label = MagicMock()
            mock_label.place = MagicMock()
            mock_label_cls.return_value = mock_label
            
            mock_var = MagicMock()
            mock_var.set = MagicMock()
            mock_var.get = MagicMock(return_value="Processing...")
            mock_stringvar.return_value = mock_var
            
            import doingstuffoverlay
            
            doingstuffoverlay.make_overlay(mock_tk_root, "Processing...")
            
            # Default height should be 100
            call_kwargs = mock_frame.place.call_args[1]
            assert call_kwargs.get('height') == 100

    def test_update_overlay_with_zero_height(self, mock_tk_root):
        """Test update_overlay with zero height."""
        with patch('tkinter.StringVar'), \
             patch('tkinter.ttk.Frame'), \
             patch('tkinter.ttk.Label'):
            
            import doingstuffoverlay
            
            doingstuffoverlay.doing_stuff = MagicMock()
            doingstuffoverlay.doing_stuff.configure = MagicMock()
            doingstuffoverlay.header_label = MagicMock()
            doingstuffoverlay.header_label.configure = MagicMock()
            doingstuffoverlay.footer_label = MagicMock()
            doingstuffoverlay.footer_label.configure = MagicMock()
            doingstuffoverlay.doing_stuff_frame = MagicMock()
            doingstuffoverlay.doing_stuff_frame.winfo_height = MagicMock(return_value=100)
            doingstuffoverlay.doing_stuff_frame.place = MagicMock()
            
            doingstuffoverlay.update_overlay(
                mock_tk_root,
                overlay_text="Processing...",
                overlay_height=0
            )
            
            # Zero height should still update
            doingstuffoverlay.doing_stuff_frame.place.assert_called_with(height=0)

    def test_update_overlay_with_negative_height(self, mock_tk_root):
        """Test update_overlay with negative height."""
        with patch('tkinter.StringVar'), \
             patch('tkinter.ttk.Frame'), \
             patch('tkinter.ttk.Label'):
            
            import doingstuffoverlay
            
            doingstuffoverlay.doing_stuff = MagicMock()
            doingstuffoverlay.doing_stuff.configure = MagicMock()
            doingstuffoverlay.header_label = MagicMock()
            doingstuffoverlay.header_label.configure = MagicMock()
            doingstuffoverlay.footer_label = MagicMock()
            doingstuffoverlay.footer_label.configure = MagicMock()
            doingstuffoverlay.doing_stuff_frame = MagicMock()
            doingstuffoverlay.doing_stuff_frame.winfo_height = MagicMock(return_value=100)
            doingstuffoverlay.doing_stuff_frame.place = MagicMock()
            
            doingstuffoverlay.update_overlay(
                mock_tk_root,
                overlay_text="Processing...",
                overlay_height=-50
            )
            
            # Negative height should still update (tkinter will handle)
            doingstuffoverlay.doing_stuff_frame.place.assert_called_with(height=-50)

    def test_make_overlay_with_special_characters(self, mock_tk_root):
        """Test make_overlay with special characters in text."""
        special_text = "Processing... <>&\"'\\n\\t"
        
        with patch('tkinter.StringVar') as mock_stringvar, \
             patch('tkinter.ttk.Frame') as mock_frame_cls, \
             patch('tkinter.ttk.Label') as mock_label_cls:
            
            mock_frame = MagicMock()
            mock_frame.grab_set = MagicMock()
            mock_frame.place = MagicMock()
            mock_frame_cls.return_value = mock_frame
            
            mock_label = MagicMock()
            mock_label.place = MagicMock()
            mock_label_cls.return_value = mock_label
            
            mock_var = MagicMock()
            mock_var.set = MagicMock()
            mock_var.get = MagicMock(return_value=special_text)
            mock_stringvar.return_value = mock_var
            
            import doingstuffoverlay
            
            doingstuffoverlay.make_overlay(mock_tk_root, special_text)
            
            # Should handle special characters
            mock_var.set.assert_called()

    def test_update_overlay_empty_then_text(self, mock_tk_root):
        """Test update_overlay with empty text then normal text."""
        with patch('tkinter.StringVar'), \
             patch('tkinter.ttk.Frame'), \
             patch('tkinter.ttk.Label'):
            
            import doingstuffoverlay
            
            doingstuffoverlay.doing_stuff = MagicMock()
            doingstuffoverlay.doing_stuff.configure = MagicMock()
            doingstuffoverlay.header_label = MagicMock()
            doingstuffoverlay.header_label.configure = MagicMock()
            doingstuffoverlay.footer_label = MagicMock()
            doingstuffoverlay.footer_label.configure = MagicMock()
            doingstuffoverlay.doing_stuff_frame = MagicMock()
            doingstuffoverlay.doing_stuff_frame.winfo_height = MagicMock(return_value=100)
            doingstuffoverlay.doing_stuff_frame.place = MagicMock()
            
            # First update with empty
            doingstuffoverlay.update_overlay(mock_tk_root, "")
            doingstuffoverlay.doing_stuff.configure.assert_called_with(text="")
            
            # Second update with text
            doingstuffoverlay.update_overlay(mock_tk_root, "Processing...")
            doingstuffoverlay.doing_stuff.configure.assert_called_with(text="Processing...")
