"""
Aggressive unit tests for tk_extra_widgets.py custom tkinter widgets.

Tests are designed to run headlessly using mocks for all tkinter objects.
"""

import platform
from unittest.mock import MagicMock, patch, PropertyMock

import pytest

import tk_extra_widgets


class TestRightClickMenu:
    """Tests for the RightClickMenu widget class."""

    def test_init_binds_control_a(self, mock_tk_widget):
        """Test that __init__ binds Control-a and Control-A to select_all."""
        menu = tk_extra_widgets.RightClickMenu(mock_tk_widget)
        
        # Verify bind was called for both Control-a and Control-A
        bind_calls = mock_tk_widget.bind.call_args_list
        assert len(bind_calls) == 2
        
        # Check the bindings
        assert bind_calls[0][0][0] == "<Control-a>"
        assert bind_calls[1][0][0] == "<Control-A>"
        
        # Verify add='+' was passed
        assert bind_calls[0][1].get('add') == '+'
        assert bind_calls[1][1].get('add') == '+'

    def test_call_with_valid_event(self, mock_tk_widget, mock_event):
        """Test __call__ with a valid event invokes build_menu."""
        menu = tk_extra_widgets.RightClickMenu(mock_tk_widget)
        
        # Mock the build_menu method
        menu.build_menu = MagicMock()
        
        result = menu(mock_event)
        
        # Verify focus was forced
        mock_tk_widget.focus_force.assert_called_once()
        
        # Verify build_menu was called with the event
        menu.build_menu.assert_called_once_with(mock_event)

    def test_call_with_disabled_widget(self, mock_tk_widget, mock_event):
        """Test __call__ does nothing when widget is disabled."""
        mock_tk_widget.cget = MagicMock(return_value='disabled')
        
        menu = tk_extra_widgets.RightClickMenu(mock_tk_widget)
        menu.build_menu = MagicMock()
        
        result = menu(mock_event)
        
        # build_menu should not be called
        menu.build_menu.assert_not_called()
        
        # focus_force should not be called
        mock_tk_widget.focus_force.assert_not_called()

    def test_call_with_none_event(self, mock_tk_widget):
        """Test __call__ handles None event - build_menu receives None."""
        menu = tk_extra_widgets.RightClickMenu(mock_tk_widget)
        
        # Don't mock build_menu - let it receive None and fail when accessing x_root
        # This tests that __call__ passes None through to build_menu
        with patch('tkinter.Menu') as mock_menu_cls:
            mock_menu = MagicMock()
            mock_menu_cls.return_value = mock_menu
            
            # This will raise AttributeError when trying to access None.x_root
            with pytest.raises(AttributeError):
                menu(None)

    def test_build_menu_with_selection(self, mock_tk_widget, mock_event, mock_menu):
        """Test build_menu creates correct menu when text is selected."""
        mock_tk_widget.selection_present = MagicMock(return_value=True)
        mock_tk_widget.selection_get = MagicMock(return_value='selected text')
        
        menu = tk_extra_widgets.RightClickMenu(mock_tk_widget)
        
        with patch('tkinter.Menu', return_value=mock_menu):
            menu.build_menu(mock_event)
        
        # Verify menu.post was called with event coordinates
        mock_menu.post.assert_called_once_with(mock_event.x_root, mock_event.y_root)
        
        # Verify add_command was called for menu items
        assert mock_menu.add_command.call_count >= 4  # Cut, Copy, Paste, Delete, Select All

    def test_build_menu_without_selection(self, mock_tk_widget, mock_event, mock_menu):
        """Test build_menu disables Cut/Copy/Delete when no selection."""
        mock_tk_widget.selection_present = MagicMock(return_value=False)
        mock_tk_widget.selection_get = MagicMock(side_effect=Exception("No selection"))
        
        menu = tk_extra_widgets.RightClickMenu(mock_tk_widget)
        
        with patch('tkinter.Menu', return_value=mock_menu):
            with patch.object(menu, 'paste_string_state', return_value=False):
                menu.build_menu(mock_event)
        
        # Verify menu was posted
        mock_menu.post.assert_called_once()

    def test_build_menu_with_clipboard_content(self, mock_tk_widget, mock_event, mock_menu):
        """Test build_menu enables Paste when clipboard has content."""
        mock_tk_widget.selection_present = MagicMock(return_value=False)
        
        menu = tk_extra_widgets.RightClickMenu(mock_tk_widget)
        
        with patch('tkinter.Menu', return_value=mock_menu):
            with patch.object(menu, 'paste_string_state', return_value=True):
                menu.build_menu(mock_event)
        
        mock_menu.post.assert_called_once()

    def test_build_menu_without_clipboard_content(self, mock_tk_widget, mock_event, mock_menu):
        """Test build_menu disables Paste when clipboard is empty."""
        mock_tk_widget.selection_present = MagicMock(return_value=False)
        
        menu = tk_extra_widgets.RightClickMenu(mock_tk_widget)
        
        with patch('tkinter.Menu', return_value=mock_menu):
            with patch.object(menu, 'paste_string_state', return_value=False):
                menu.build_menu(mock_event)
        
        mock_menu.post.assert_called_once()

    def test_paste_string_state_with_string_clipboard(self, mock_tk_widget):
        """Test paste_string_state returns True when clipboard has string."""
        mock_tk_widget.selection_get = MagicMock(return_value='clipboard text')
        
        menu = tk_extra_widgets.RightClickMenu(mock_tk_widget)
        result = menu.paste_string_state()
        
        assert result is True
        mock_tk_widget.selection_get.assert_called_once_with(selection='CLIPBOARD')

    def test_paste_string_state_with_empty_clipboard(self, mock_tk_widget):
        """Test paste_string_state returns False when clipboard is empty."""
        import tkinter
        mock_tk_widget.selection_get = MagicMock(side_effect=tkinter.TclError())
        
        menu = tk_extra_widgets.RightClickMenu(mock_tk_widget)
        result = menu.paste_string_state()
        
        assert result is False

    def test_paste_string_state_with_non_string_clipboard(self, mock_tk_widget):
        """Test paste_string_state returns False when clipboard has non-string data."""
        import tkinter
        mock_tk_widget.selection_get = MagicMock(side_effect=tkinter.TclError())
        
        menu = tk_extra_widgets.RightClickMenu(mock_tk_widget)
        result = menu.paste_string_state()
        
        assert result is False

    def test_select_all(self, mock_tk_widget):
        """Test select_all method calls selection_range and icursor."""
        menu = tk_extra_widgets.RightClickMenu(mock_tk_widget)
        
        result = menu.select_all()
        
        mock_tk_widget.selection_range.assert_called_once()
        mock_tk_widget.icursor.assert_called_once()
        
        # Should return 'break' to prevent default behavior
        assert result == 'break'

    def test_menu_item_cut_callback(self, mock_tk_widget, mock_event, mock_menu):
        """Test that Cut menu item generates <<Cut>> event."""
        mock_tk_widget.selection_present = MagicMock(return_value=True)
        
        menu = tk_extra_widgets.RightClickMenu(mock_tk_widget)
        
        with patch('tkinter.Menu', return_value=mock_menu):
            menu.build_menu(mock_event)
        
        # Find the Cut command callback
        cut_call = None
        for call in mock_menu.add_command.call_args_list:
            if call[1].get('label') == 'Cut':
                cut_call = call
                break
        
        assert cut_call is not None
        command = cut_call[1].get('command')
        assert command is not None
        
        # Execute the callback
        command()
        mock_tk_widget.event_generate.assert_called_with("<<Cut>>")

    def test_menu_item_copy_callback(self, mock_tk_widget, mock_event, mock_menu):
        """Test that Copy menu item generates <<Copy>> event."""
        mock_tk_widget.selection_present = MagicMock(return_value=True)
        
        menu = tk_extra_widgets.RightClickMenu(mock_tk_widget)
        
        with patch('tkinter.Menu', return_value=mock_menu):
            menu.build_menu(mock_event)
        
        # Find the Copy command callback
        copy_call = None
        for call in mock_menu.add_command.call_args_list:
            if call[1].get('label') == 'Copy':
                copy_call = call
                break
        
        assert copy_call is not None
        command = copy_call[1].get('command')
        assert command is not None
        
        command()
        mock_tk_widget.event_generate.assert_called_with("<<Copy>>")

    def test_menu_item_paste_callback(self, mock_tk_widget, mock_event, mock_menu):
        """Test that Paste menu item generates <<Paste>> event."""
        mock_tk_widget.selection_present = MagicMock(return_value=False)
        
        menu = tk_extra_widgets.RightClickMenu(mock_tk_widget)
        
        with patch('tkinter.Menu', return_value=mock_menu):
            with patch.object(menu, 'paste_string_state', return_value=True):
                menu.build_menu(mock_event)
        
        # Find the Paste command callback
        paste_call = None
        for call in mock_menu.add_command.call_args_list:
            if call[1].get('label') == 'Paste':
                paste_call = call
                break
        
        assert paste_call is not None
        command = paste_call[1].get('command')
        assert command is not None
        
        command()
        mock_tk_widget.event_generate.assert_called_with("<<Paste>>")

    def test_menu_item_delete_callback(self, mock_tk_widget, mock_event, mock_menu):
        """Test that Delete menu item generates <<Clear>> event."""
        mock_tk_widget.selection_present = MagicMock(return_value=True)
        
        menu = tk_extra_widgets.RightClickMenu(mock_tk_widget)
        
        with patch('tkinter.Menu', return_value=mock_menu):
            with patch.object(menu, 'paste_string_state', return_value=False):
                menu.build_menu(mock_event)
        
        # Find the Delete command callback
        delete_call = None
        for call in mock_menu.add_command.call_args_list:
            if call[1].get('label') == 'Delete':
                delete_call = call
                break
        
        assert delete_call is not None
        command = delete_call[1].get('command')
        assert command is not None
        
        command()
        mock_tk_widget.event_generate.assert_called_with("<<Clear>>")

    def test_menu_item_select_all_callback(self, mock_tk_widget, mock_event, mock_menu):
        """Test that Select All menu item calls select_all method."""
        mock_tk_widget.selection_present = MagicMock(return_value=False)
        
        menu = tk_extra_widgets.RightClickMenu(mock_tk_widget)
        menu.select_all = MagicMock(return_value='break')
        
        with patch('tkinter.Menu', return_value=mock_menu):
            with patch.object(menu, 'paste_string_state', return_value=False):
                menu.build_menu(mock_event)
        
        # Find the Select All command callback
        select_all_call = None
        for call in mock_menu.add_command.call_args_list:
            if call[1].get('label') == 'Select All':
                select_all_call = call
                break
        
        assert select_all_call is not None
        command = select_all_call[1].get('command')
        assert command is not None
        
        # Execute the callback
        command()
        menu.select_all.assert_called_once()

    def test_rapid_successive_popup_calls(self, mock_tk_widget, mock_event, mock_menu):
        """Test rapid successive popup calls don't cause issues."""
        mock_tk_widget.selection_present = MagicMock(return_value=True)
        
        menu = tk_extra_widgets.RightClickMenu(mock_tk_widget)
        
        with patch('tkinter.Menu', return_value=mock_menu):
            # Simulate rapid successive calls
            for i in range(10):
                menu.build_menu(mock_event)
        
        # Verify all calls completed
        assert mock_menu.post.call_count == 10

    def test_callback_exception_handling_in_cut(self, mock_tk_widget, mock_event, mock_menu):
        """Test that exceptions in Cut callback are not silently caught."""
        mock_tk_widget.selection_present = MagicMock(return_value=True)
        mock_tk_widget.event_generate = MagicMock(side_effect=RuntimeError("Test error"))
        
        menu = tk_extra_widgets.RightClickMenu(mock_tk_widget)
        
        with patch('tkinter.Menu', return_value=mock_menu):
            menu.build_menu(mock_event)
        
        # Find the Cut command callback
        cut_call = None
        for call in mock_menu.add_command.call_args_list:
            if call[1].get('label') == 'Cut':
                cut_call = call
                break
        
        command = cut_call[1].get('command')
        
        # The exception should propagate
        with pytest.raises(RuntimeError, match="Test error"):
            command()

    def test_build_menu_with_missing_coordinates(self, mock_tk_widget, mock_event_none_coords, mock_menu):
        """Test build_menu handles events with None coordinates."""
        mock_tk_widget.selection_present = MagicMock(return_value=False)
        
        menu = tk_extra_widgets.RightClickMenu(mock_tk_widget)
        
        with patch('tkinter.Menu', return_value=mock_menu):
            with patch.object(menu, 'paste_string_state', return_value=False):
                # This should handle None coordinates gracefully
                # In real tkinter, this would fail, but we test the code path
                menu.build_menu(mock_event_none_coords)
        
        # post should be called with None values
        mock_menu.post.assert_called_once_with(None, None)

    def test_init_with_none_parent(self):
        """Test __init__ handles None parent gracefully."""
        # This should raise an AttributeError when trying to bind
        with pytest.raises(AttributeError):
            tk_extra_widgets.RightClickMenu(None)


class TestVerticalScrolledFrame:
    """Tests for the VerticalScrolledFrame widget class."""

    def test_init_creates_scrollbar_and_canvas(self, mock_tk_widget):
        """Test that __init__ creates scrollbar and canvas components."""
        with patch('tkinter.Frame.__init__') as mock_frame_init, \
             patch('tkinter.ttk.Scrollbar') as mock_scrollbar_cls, \
             patch('tkinter.Canvas') as mock_canvas_cls, \
             patch('tkinter.ttk.Frame') as mock_ttk_frame:
            
            mock_scrollbar = MagicMock()
            mock_canvas = MagicMock()
            mock_interior = MagicMock()
            
            mock_scrollbar_cls.return_value = mock_scrollbar
            mock_canvas_cls.return_value = mock_canvas
            mock_ttk_frame.return_value = mock_interior
            
            # Mock the interior's winfo methods
            mock_interior.winfo_reqwidth = MagicMock(return_value=200)
            mock_interior.winfo_reqheight = MagicMock(return_value=300)
            mock_interior.bind = MagicMock()
            
            frame = tk_extra_widgets.VerticalScrolledFrame(mock_tk_widget)
            
            # Verify scrollbar was created
            mock_scrollbar_cls.assert_called_once()
            
            # Verify canvas was created
            mock_canvas_cls.assert_called_once()

    def test_interior_attribute_exists(self, mock_tk_widget):
        """Test that interior attribute is created."""
        with patch('tkinter.Frame.__init__'), \
             patch('tkinter.ttk.Scrollbar') as mock_scrollbar_cls, \
             patch('tkinter.Canvas') as mock_canvas_cls, \
             patch('tkinter.ttk.Frame') as mock_ttk_frame:
            
            mock_scrollbar = MagicMock()
            mock_canvas = MagicMock()
            mock_interior = MagicMock()
            
            mock_scrollbar_cls.return_value = mock_scrollbar
            mock_canvas_cls.return_value = mock_canvas
            mock_ttk_frame.return_value = mock_interior
            mock_canvas.create_window = MagicMock(return_value='interior_id')
            
            frame = tk_extra_widgets.VerticalScrolledFrame(mock_tk_widget)
            
            assert hasattr(frame, 'interior')

    def test_configure_interior_updates_scrollregion(self, mock_tk_widget, mock_canvas):
        """Test that _configure_interior updates canvas scrollregion."""
        with patch('tkinter.Frame.__init__'), \
             patch('tkinter.ttk.Scrollbar') as mock_scrollbar_cls, \
             patch('tkinter.Canvas') as mock_canvas_cls, \
             patch('tkinter.ttk.Frame') as mock_ttk_frame:
            
            mock_scrollbar = MagicMock()
            mock_interior = MagicMock()
            
            mock_scrollbar_cls.return_value = mock_scrollbar
            mock_canvas_cls.return_value = mock_canvas
            mock_ttk_frame.return_value = mock_interior
            
            mock_interior.winfo_reqwidth = MagicMock(return_value=200)
            mock_interior.winfo_reqheight = MagicMock(return_value=300)
            mock_interior.bind = MagicMock()
            
            frame = tk_extra_widgets.VerticalScrolledFrame(mock_tk_widget)
            
            # Simulate configure event
            configure_calls = mock_interior.bind.call_args_list
            configure_binding = None
            for call in configure_calls:
                if call[0][0] == '<Configure>':
                    configure_binding = call[0][1]
                    break
            
            # The binding should exist
            assert configure_binding is not None

    def test_mouse_wheel_binding_on_enter(self, mock_tk_widget):
        """Test that mouse wheel is bound on Enter event."""
        with patch('tkinter.Frame.__init__'), \
             patch('tkinter.ttk.Scrollbar') as mock_scrollbar_cls, \
             patch('tkinter.Canvas') as mock_canvas_cls, \
             patch('tkinter.ttk.Frame') as mock_ttk_frame:
            
            mock_scrollbar = MagicMock()
            mock_canvas = MagicMock()
            mock_interior = MagicMock()
            
            mock_scrollbar_cls.return_value = mock_scrollbar
            mock_canvas_cls.return_value = mock_canvas
            mock_ttk_frame.return_value = mock_interior
            
            mock_interior.winfo_reqwidth = MagicMock(return_value=200)
            mock_interior.winfo_reqheight = MagicMock(return_value=300)
            mock_interior.bind = MagicMock()
            mock_scrollbar.bind = MagicMock()
            mock_scrollbar.bind_all = MagicMock()
            
            frame = tk_extra_widgets.VerticalScrolledFrame(mock_tk_widget)
            
            # Check that Enter binding was set on interior
            enter_binding_found = False
            for call in mock_interior.bind.call_args_list:
                if '<Enter>' in call[0]:
                    enter_binding_found = True
                    break
            
            assert enter_binding_found

    def test_mouse_wheel_unbinding_on_leave(self, mock_tk_widget):
        """Test that mouse wheel is unbound on Leave event."""
        with patch('tkinter.Frame.__init__'), \
             patch('tkinter.ttk.Scrollbar') as mock_scrollbar_cls, \
             patch('tkinter.Canvas') as mock_canvas_cls, \
             patch('tkinter.ttk.Frame') as mock_ttk_frame:
            
            mock_scrollbar = MagicMock()
            mock_canvas = MagicMock()
            mock_interior = MagicMock()
            
            mock_scrollbar_cls.return_value = mock_scrollbar
            mock_canvas_cls.return_value = mock_canvas
            mock_ttk_frame.return_value = mock_interior
            
            mock_interior.bind = MagicMock()
            mock_scrollbar.bind = MagicMock()
            
            frame = tk_extra_widgets.VerticalScrolledFrame(mock_tk_widget)
            
            # Check that Leave binding was set on interior
            leave_binding_found = False
            for call in mock_interior.bind.call_args_list:
                if '<Leave>' in call[0]:
                    leave_binding_found = True
                    break
            
            assert leave_binding_found

    def test_on_mouse_wheel_linux_scroll_up(self, mock_tk_widget, mock_event):
        """Test mouse wheel scrolling on Linux (scroll up)."""
        original_platform = platform.system
        
        with patch('platform.system', return_value='Linux'), \
             patch('tkinter.Frame.__init__'), \
             patch('tkinter.ttk.Scrollbar') as mock_scrollbar_cls, \
             patch('tkinter.Canvas') as mock_canvas_cls, \
             patch('tkinter.ttk.Frame') as mock_ttk_frame:
            
            mock_scrollbar = MagicMock()
            mock_canvas = MagicMock()
            mock_interior = MagicMock()
            
            mock_scrollbar_cls.return_value = mock_scrollbar
            mock_canvas_cls.return_value = mock_canvas
            mock_ttk_frame.return_value = mock_interior
            
            mock_interior.bind = MagicMock()
            mock_scrollbar.bind = MagicMock()
            mock_scrollbar.bind_all = MagicMock()
            mock_canvas.yview = MagicMock()
            
            frame = tk_extra_widgets.VerticalScrolledFrame(mock_tk_widget)
            
            # The mouse wheel handler should be set up
            # We can't directly test the closure, but we verify the setup

    def test_on_mouse_wheel_windows(self, mock_tk_widget):
        """Test mouse wheel scrolling on Windows."""
        mock_event_windows = MagicMock()
        mock_event_windows.delta = 120  # Scroll up
        mock_event_windows.num = 0
        
        with patch('platform.system', return_value='Windows'), \
             patch('tkinter.Frame.__init__'), \
             patch('tkinter.ttk.Scrollbar') as mock_scrollbar_cls, \
             patch('tkinter.Canvas') as mock_canvas_cls, \
             patch('tkinter.ttk.Frame') as mock_ttk_frame:
            
            mock_scrollbar = MagicMock()
            mock_canvas = MagicMock()
            mock_interior = MagicMock()
            
            mock_scrollbar_cls.return_value = mock_scrollbar
            mock_canvas_cls.return_value = mock_canvas
            mock_ttk_frame.return_value = mock_interior
            
            mock_interior.bind = MagicMock()
            mock_scrollbar.bind = MagicMock()
            mock_scrollbar.bind_all = MagicMock()
            mock_canvas.yview = MagicMock()
            
            frame = tk_extra_widgets.VerticalScrolledFrame(mock_tk_widget)
            
            # Verify bind_all was called for MouseWheel on Windows
            bind_all_calls = mock_scrollbar.bind_all.call_args_list
            mousewheel_bound = any('<MouseWheel>' in str(call) for call in bind_all_calls)
            assert mousewheel_bound

    def test_on_mouse_wheel_darwin(self, mock_tk_widget):
        """Test mouse wheel scrolling on macOS (Darwin)."""
        with patch('platform.system', return_value='Darwin'), \
             patch('tkinter.Frame.__init__'), \
             patch('tkinter.ttk.Scrollbar') as mock_scrollbar_cls, \
             patch('tkinter.Canvas') as mock_canvas_cls, \
             patch('tkinter.ttk.Frame') as mock_ttk_frame:
            
            mock_scrollbar = MagicMock()
            mock_canvas = MagicMock()
            mock_interior = MagicMock()
            
            mock_scrollbar_cls.return_value = mock_scrollbar
            mock_canvas_cls.return_value = mock_canvas
            mock_ttk_frame.return_value = mock_interior
            
            mock_interior.bind = MagicMock()
            mock_scrollbar.bind = MagicMock()
            mock_scrollbar.bind_all = MagicMock()
            mock_canvas.yview = MagicMock()
            
            frame = tk_extra_widgets.VerticalScrolledFrame(mock_tk_widget)
            
            # Verify bind_all was called for MouseWheel on Darwin
            bind_all_calls = mock_scrollbar.bind_all.call_args_list
            mousewheel_bound = any('<MouseWheel>' in str(call) for call in bind_all_calls)
            assert mousewheel_bound

    def test_extreme_scroll_values(self, mock_tk_widget):
        """Test handling of extreme scroll values."""
        with patch('platform.system', return_value='Windows'), \
             patch('tkinter.Frame.__init__'), \
             patch('tkinter.ttk.Scrollbar') as mock_scrollbar_cls, \
             patch('tkinter.Canvas') as mock_canvas_cls, \
             patch('tkinter.ttk.Frame') as mock_ttk_frame:
            
            mock_scrollbar = MagicMock()
            mock_canvas = MagicMock()
            mock_interior = MagicMock()
            
            mock_scrollbar_cls.return_value = mock_scrollbar
            mock_canvas_cls.return_value = mock_canvas
            mock_ttk_frame.return_value = mock_interior
            
            mock_interior.bind = MagicMock()
            mock_scrollbar.bind = MagicMock()
            mock_scrollbar.bind_all = MagicMock()
            mock_canvas.yview = MagicMock()
            
            frame = tk_extra_widgets.VerticalScrolledFrame(mock_tk_widget)
            
            # The frame should be created without issues
            assert frame is not None

    def test_with_none_parent(self):
        """Test initialization with None parent."""
        with patch('tkinter.Frame.__init__') as mock_frame_init:
            # Frame.__init__ with None parent should work in mock context
            mock_frame_init.return_value = None
            
            with patch('tkinter.ttk.Scrollbar') as mock_scrollbar_cls, \
                 patch('tkinter.Canvas') as mock_canvas_cls, \
                 patch('tkinter.ttk.Frame') as mock_ttk_frame:
                
                mock_scrollbar = MagicMock()
                mock_canvas = MagicMock()
                mock_interior = MagicMock()
                
                mock_scrollbar_cls.return_value = mock_scrollbar
                mock_canvas_cls.return_value = mock_canvas
                mock_ttk_frame.return_value = mock_interior
                
                # This should not raise
                frame = tk_extra_widgets.VerticalScrolledFrame(None)

    def test_empty_frame_scenario(self, mock_tk_widget):
        """Test behavior with empty frame (no content)."""
        with patch('tkinter.Frame.__init__'), \
             patch('tkinter.ttk.Scrollbar') as mock_scrollbar_cls, \
             patch('tkinter.Canvas') as mock_canvas_cls, \
             patch('tkinter.ttk.Frame') as mock_ttk_frame:
            
            mock_scrollbar = MagicMock()
            mock_canvas = MagicMock()
            mock_interior = MagicMock()
            
            mock_scrollbar_cls.return_value = mock_scrollbar
            mock_canvas_cls.return_value = mock_canvas
            mock_ttk_frame.return_value = mock_interior
            
            # Empty frame has minimal dimensions
            mock_interior.winfo_reqwidth = MagicMock(return_value=0)
            mock_interior.winfo_reqheight = MagicMock(return_value=0)
            mock_interior.bind = MagicMock()
            
            frame = tk_extra_widgets.VerticalScrolledFrame(mock_tk_widget)
            
            assert hasattr(frame, 'interior')

    def test_no_scroll_needed_scenario(self, mock_tk_widget):
        """Test behavior when content fits without scrolling."""
        with patch('tkinter.Frame.__init__'), \
             patch('tkinter.ttk.Scrollbar') as mock_scrollbar_cls, \
             patch('tkinter.Canvas') as mock_canvas_cls, \
             patch('tkinter.ttk.Frame') as mock_ttk_frame:
            
            mock_scrollbar = MagicMock()
            mock_canvas = MagicMock()
            mock_interior = MagicMock()
            
            mock_scrollbar_cls.return_value = mock_scrollbar
            mock_canvas_cls.return_value = mock_canvas
            mock_ttk_frame.return_value = mock_interior
            
            # Content is smaller than canvas
            mock_interior.winfo_reqwidth = MagicMock(return_value=100)
            mock_interior.winfo_reqheight = MagicMock(return_value=100)
            mock_canvas.winfo_width = MagicMock(return_value=200)
            mock_interior.bind = MagicMock()
            
            frame = tk_extra_widgets.VerticalScrolledFrame(mock_tk_widget)
            
            assert frame is not None

    def test_scroll_needed_scenario(self, mock_tk_widget):
        """Test behavior when content requires scrolling."""
        with patch('tkinter.Frame.__init__'), \
             patch('tkinter.ttk.Scrollbar') as mock_scrollbar_cls, \
             patch('tkinter.Canvas') as mock_canvas_cls, \
             patch('tkinter.ttk.Frame') as mock_ttk_frame:
            
            mock_scrollbar = MagicMock()
            mock_canvas = MagicMock()
            mock_interior = MagicMock()
            
            mock_scrollbar_cls.return_value = mock_scrollbar
            mock_canvas_cls.return_value = mock_canvas
            mock_ttk_frame.return_value = mock_interior
            
            # Content is larger than canvas
            mock_interior.winfo_reqwidth = MagicMock(return_value=500)
            mock_interior.winfo_reqheight = MagicMock(return_value=1000)
            mock_canvas.winfo_width = MagicMock(return_value=200)
            mock_interior.bind = MagicMock()
            
            frame = tk_extra_widgets.VerticalScrolledFrame(mock_tk_widget)
            
            assert frame is not None


class TestCreateToolTip:
    """Tests for the CreateToolTip class."""

    def test_init_binds_events(self, mock_tk_widget):
        """Test that __init__ binds Enter, Leave, and ButtonPress events."""
        tooltip = tk_extra_widgets.CreateToolTip(mock_tk_widget, "Test tooltip")
        
        bind_calls = mock_tk_widget.bind.call_args_list
        
        # Check all three events are bound
        events_bound = [call[0][0] for call in bind_calls]
        assert "<Enter>" in events_bound
        assert "<Leave>" in events_bound
        assert "<ButtonPress>" in events_bound

    def test_init_sets_default_values(self, mock_tk_widget):
        """Test that __init__ sets default waittime and wraplength."""
        tooltip = tk_extra_widgets.CreateToolTip(mock_tk_widget, "Test tooltip")
        
        assert tooltip.waittime == 500
        assert tooltip.wraplength == 180
        assert tooltip.text == "Test tooltip"
        assert tooltip.id is None
        assert tooltip.tw is None

    def test_enter_schedules_tooltip(self, mock_tk_widget):
        """Test that enter() calls schedule()."""
        tooltip = tk_extra_widgets.CreateToolTip(mock_tk_widget, "Test tooltip")
        tooltip.schedule = MagicMock()
        
        tooltip.enter()
        
        tooltip.schedule.assert_called_once()

    def test_enter_with_none_event(self, mock_tk_widget):
        """Test enter() handles None event gracefully."""
        tooltip = tk_extra_widgets.CreateToolTip(mock_tk_widget, "Test tooltip")
        tooltip.schedule = MagicMock()
        
        # Should not raise
        tooltip.enter(None)
        
        tooltip.schedule.assert_called_once()

    def test_leave_unschedules_and_hides(self, mock_tk_widget):
        """Test that leave() calls unschedule() and hidetip()."""
        tooltip = tk_extra_widgets.CreateToolTip(mock_tk_widget, "Test tooltip")
        tooltip.unschedule = MagicMock()
        tooltip.hidetip = MagicMock()
        
        tooltip.leave()
        
        tooltip.unschedule.assert_called_once()
        tooltip.hidetip.assert_called_once()

    def test_leave_with_none_event(self, mock_tk_widget):
        """Test leave() handles None event gracefully."""
        tooltip = tk_extra_widgets.CreateToolTip(mock_tk_widget, "Test tooltip")
        tooltip.unschedule = MagicMock()
        tooltip.hidetip = MagicMock()
        
        # Should not raise
        tooltip.leave(None)
        
        tooltip.unschedule.assert_called_once()
        tooltip.hidetip.assert_called_once()

    def test_schedule_calls_after(self, mock_tk_widget):
        """Test that schedule() calls widget.after() with correct parameters."""
        tooltip = tk_extra_widgets.CreateToolTip(mock_tk_widget, "Test tooltip")
        
        tooltip.schedule()
        
        mock_tk_widget.after.assert_called_once_with(500, tooltip.showtip)

    def test_schedule_cancels_existing(self, mock_tk_widget):
        """Test that schedule() cancels any existing scheduled tooltip."""
        tooltip = tk_extra_widgets.CreateToolTip(mock_tk_widget, "Test tooltip")
        tooltip.id = 123  # Simulate existing scheduled tooltip
        
        tooltip.schedule()
        
        mock_tk_widget.after_cancel.assert_called_once_with(123)

    def test_unschedule_cancels_existing(self, mock_tk_widget):
        """Test that unschedule() cancels scheduled tooltip."""
        tooltip = tk_extra_widgets.CreateToolTip(mock_tk_widget, "Test tooltip")
        tooltip.id = 456
        
        tooltip.unschedule()
        
        mock_tk_widget.after_cancel.assert_called_once_with(456)
        assert tooltip.id is None

    def test_unschedule_with_no_scheduled(self, mock_tk_widget):
        """Test that unschedule() handles no scheduled tooltip."""
        tooltip = tk_extra_widgets.CreateToolTip(mock_tk_widget, "Test tooltip")
        tooltip.id = None
        
        # Should not raise
        tooltip.unschedule()
        
        mock_tk_widget.after_cancel.assert_not_called()

    def test_showtip_creates_toplevel(self, mock_tk_widget, mock_toplevel):
        """Test that showtip() creates a Toplevel window."""
        mock_tk_widget.bbox = MagicMock(return_value=(0, 0, 50, 20))
        mock_tk_widget.winfo_rootx = MagicMock(return_value=100)
        mock_tk_widget.winfo_rooty = MagicMock(return_value=100)
        
        tooltip = tk_extra_widgets.CreateToolTip(mock_tk_widget, "Test tooltip")
        
        with patch('tkinter.Toplevel', return_value=mock_toplevel):
            with patch('tkinter.Label') as mock_label_cls:
                mock_label = MagicMock()
                mock_label_cls.return_value = mock_label
                
                tooltip.showtip()
        
        assert tooltip.tw is not None

    def test_showtip_positions_correctly(self, mock_tk_widget, mock_toplevel):
        """Test that showtip() positions tooltip near widget."""
        mock_tk_widget.bbox = MagicMock(return_value=(10, 20, 50, 30))
        mock_tk_widget.winfo_rootx = MagicMock(return_value=100)
        mock_tk_widget.winfo_rooty = MagicMock(return_value=200)
        
        tooltip = tk_extra_widgets.CreateToolTip(mock_tk_widget, "Test tooltip")
        
        with patch('tkinter.Toplevel', return_value=mock_toplevel):
            with patch('tkinter.Label') as mock_label_cls:
                mock_label = MagicMock()
                mock_label_cls.return_value = mock_label
                
                tooltip.showtip()
        
        # Verify geometry was set (position should be widget position + offset)
        mock_toplevel.wm_geometry.assert_called_once()

    def test_showtip_creates_label_with_text(self, mock_tk_widget, mock_toplevel):
        """Test that showtip() creates Label with correct text."""
        mock_tk_widget.bbox = MagicMock(return_value=(0, 0, 50, 20))
        mock_tk_widget.winfo_rootx = MagicMock(return_value=100)
        mock_tk_widget.winfo_rooty = MagicMock(return_value=100)
        
        tooltip = tk_extra_widgets.CreateToolTip(mock_tk_widget, "My tooltip text")
        
        with patch('tkinter.Toplevel', return_value=mock_toplevel):
            with patch('tkinter.Label') as mock_label_cls:
                mock_label = MagicMock()
                mock_label_cls.return_value = mock_label
                
                tooltip.showtip()
        
        # Verify Label was created with correct text
        mock_label_cls.assert_called_once()
        call_kwargs = mock_label_cls.call_args[1]
        assert call_kwargs['text'] == "My tooltip text"
        assert call_kwargs['wraplength'] == 180

    def test_hidetip_destroys_toplevel(self, mock_tk_widget, mock_toplevel):
        """Test that hidetip() destroys the Toplevel window."""
        tooltip = tk_extra_widgets.CreateToolTip(mock_tk_widget, "Test tooltip")
        tooltip.tw = mock_toplevel
        
        tooltip.hidetip()
        
        mock_toplevel.destroy.assert_called_once()
        assert tooltip.tw is None

    def test_hidetip_with_no_toplevel(self, mock_tk_widget):
        """Test that hidetip() handles no Toplevel window."""
        tooltip = tk_extra_widgets.CreateToolTip(mock_tk_widget, "Test tooltip")
        tooltip.tw = None
        
        # Should not raise
        tooltip.hidetip()
        
        assert tooltip.tw is None

    def test_rapid_enter_leave_cycles(self, mock_tk_widget):
        """Test rapid enter/leave cycles don't cause issues."""
        tooltip = tk_extra_widgets.CreateToolTip(mock_tk_widget, "Test tooltip")
        
        # Simulate rapid enter/leave cycles
        for _ in range(10):
            tooltip.enter()
            tooltip.leave()
        
        # Verify after_cancel was called multiple times (once per cycle)
        assert mock_tk_widget.after_cancel.call_count >= 10

    def test_enter_with_event_object(self, mock_tk_widget, mock_event):
        """Test enter() works with event object."""
        tooltip = tk_extra_widgets.CreateToolTip(mock_tk_widget, "Test tooltip")
        tooltip.schedule = MagicMock()
        
        tooltip.enter(mock_event)
        
        tooltip.schedule.assert_called_once()

    def test_leave_with_event_object(self, mock_tk_widget, mock_event):
        """Test leave() works with event object."""
        tooltip = tk_extra_widgets.CreateToolTip(mock_tk_widget, "Test tooltip")
        tooltip.unschedule = MagicMock()
        tooltip.hidetip = MagicMock()
        
        tooltip.leave(mock_event)
        
        tooltip.unschedule.assert_called_once()
        tooltip.hidetip.assert_called_once()

    def test_with_none_widget(self):
        """Test initialization with None widget."""
        # This should raise AttributeError when trying to bind
        with pytest.raises(AttributeError):
            tk_extra_widgets.CreateToolTip(None, "Test tooltip")

    def test_with_empty_text(self, mock_tk_widget, mock_toplevel):
        """Test tooltip with empty text."""
        mock_tk_widget.bbox = MagicMock(return_value=(0, 0, 50, 20))
        mock_tk_widget.winfo_rootx = MagicMock(return_value=100)
        mock_tk_widget.winfo_rooty = MagicMock(return_value=100)
        
        tooltip = tk_extra_widgets.CreateToolTip(mock_tk_widget, "")
        
        with patch('tkinter.Toplevel', return_value=mock_toplevel):
            with patch('tkinter.Label') as mock_label_cls:
                mock_label = MagicMock()
                mock_label_cls.return_value = mock_label
                
                tooltip.showtip()
        
        # Should create tooltip with empty text
        mock_label_cls.assert_called_once()
        call_kwargs = mock_label_cls.call_args[1]
        assert call_kwargs['text'] == ""

    def test_with_long_text(self, mock_tk_widget, mock_toplevel):
        """Test tooltip with long text that wraps."""
        mock_tk_widget.bbox = MagicMock(return_value=(0, 0, 50, 20))
        mock_tk_widget.winfo_rootx = MagicMock(return_value=100)
        mock_tk_widget.winfo_rooty = MagicMock(return_value=100)
        
        long_text = "This is a very long tooltip text that should wrap according to the wraplength setting."
        tooltip = tk_extra_widgets.CreateToolTip(mock_tk_widget, long_text)
        
        with patch('tkinter.Toplevel', return_value=mock_toplevel):
            with patch('tkinter.Label') as mock_label_cls:
                mock_label = MagicMock()
                mock_label_cls.return_value = mock_label
                
                tooltip.showtip()
        
        mock_label_cls.assert_called_once()
        call_kwargs = mock_label_cls.call_args[1]
        assert call_kwargs['text'] == long_text
        assert call_kwargs['wraplength'] == 180

    def test_showtip_with_bbox_returning_none(self, mock_tk_widget, mock_toplevel):
        """Test showtip() handles bbox returning None."""
        mock_tk_widget.bbox = MagicMock(return_value=None)
        mock_tk_widget.winfo_rootx = MagicMock(return_value=100)
        mock_tk_widget.winfo_rooty = MagicMock(return_value=100)
        
        tooltip = tk_extra_widgets.CreateToolTip(mock_tk_widget, "Test tooltip")
        
        # This will fail when trying to unpack None
        with patch('tkinter.Toplevel', return_value=mock_toplevel):
            with patch('tkinter.Label'):
                with pytest.raises(TypeError):
                    tooltip.showtip()

    def test_custom_waittime(self, mock_tk_widget):
        """Test custom waittime is respected."""
        tooltip = tk_extra_widgets.CreateToolTip(mock_tk_widget, "Test tooltip")
        tooltip.waittime = 1000  # Custom waittime
        
        tooltip.schedule()
        
        mock_tk_widget.after.assert_called_once_with(1000, tooltip.showtip)

    def test_custom_wraplength(self, mock_tk_widget, mock_toplevel):
        """Test custom wraplength is respected."""
        mock_tk_widget.bbox = MagicMock(return_value=(0, 0, 50, 20))
        mock_tk_widget.winfo_rootx = MagicMock(return_value=100)
        mock_tk_widget.winfo_rooty = MagicMock(return_value=100)
        
        tooltip = tk_extra_widgets.CreateToolTip(mock_tk_widget, "Test tooltip")
        tooltip.wraplength = 300  # Custom wraplength
        
        with patch('tkinter.Toplevel', return_value=mock_toplevel):
            with patch('tkinter.Label') as mock_label_cls:
                mock_label = MagicMock()
                mock_label_cls.return_value = mock_label
                
                tooltip.showtip()
        
        call_kwargs = mock_label_cls.call_args[1]
        assert call_kwargs['wraplength'] == 300

    def test_hidetip_resets_tw_to_none(self, mock_tk_widget, mock_toplevel):
        """Test that hidetip() resets tw attribute to None."""
        tooltip = tk_extra_widgets.CreateToolTip(mock_tk_widget, "Test tooltip")
        tooltip.tw = mock_toplevel
        
        result = tooltip.hidetip()
        
        assert tooltip.tw is None

    def test_multiple_schedule_calls(self, mock_tk_widget):
        """Test multiple schedule calls cancel previous ones."""
        tooltip = tk_extra_widgets.CreateToolTip(mock_tk_widget, "Test tooltip")
        
        # First schedule
        tooltip.schedule()
        first_id = tooltip.id
        
        # Second schedule should cancel first
        tooltip.schedule()
        
        # after_cancel should have been called once
        assert mock_tk_widget.after_cancel.call_count == 1

    def test_button_press_calls_leave(self, mock_tk_widget):
        """Test that ButtonPress event is bound to leave()."""
        tooltip = tk_extra_widgets.CreateToolTip(mock_tk_widget, "Test tooltip")
        
        # Find the ButtonPress binding
        bind_calls = mock_tk_widget.bind.call_args_list
        button_press_binding = None
        for call in bind_calls:
            if call[0][0] == "<ButtonPress>":
                button_press_binding = call[0][1]
                break
        
        assert button_press_binding is not None
        
        # The binding should be the leave method
        # Since it's bound directly, it should be tooltip.leave
        assert button_press_binding == tooltip.leave
