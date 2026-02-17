"""Search widget for folder list filtering.

This module provides a reusable search/filter widget for the folder list,
with support for fuzzy matching and keyboard shortcuts.
"""

import tkinter
import tkinter.ttk
from typing import Callable, Optional

import tk_extra_widgets


class SearchWidget:
    """A search/filter widget for folder list filtering.
    
    This widget provides a text entry field and filter button for searching
    and filtering folder lists. It supports fuzzy matching via thefuzz library
    and provides keyboard shortcuts (Enter to apply, Escape to clear).
    
    Attributes:
        frame: The containing frame for the widget
        entry: The search entry field
        button: The filter update button
    
    Example:
        >>> def on_filter_change(filter_text: str):
        ...     print(f"Filter changed to: {filter_text}")
        >>> search = SearchWidget(
        ...     parent=parent_frame,
        ...     initial_value="",
        ...     on_filter_change=on_filter_change,
        ...     on_escape_clear=True
        ... )
        >>> search.pack()
    """
    
    def __init__(
        self,
        parent: tkinter.ttk.Frame,
        initial_value: str = "",
        on_filter_change: Optional[Callable[[str], None]] = None,
        on_escape_clear: bool = True,
        attach_right_click_menu: bool = True,
    ):
        """Initialize the search widget.
        
        Args:
            parent: The parent frame to contain this widget
            initial_value: Initial text to populate the search field
            on_filter_change: Callback when filter changes (receives filter text)
            on_escape_clear: If True, Escape key clears the search field
            attach_right_click_menu: If True, attach right-click context menu
        """
        self._parent = parent
        self._filter_value = initial_value
        self._on_filter_change = on_filter_change
        self._on_escape_clear = on_escape_clear
        
        # Create the widget frame
        self._frame = tkinter.ttk.Frame(parent)
        
        # Create search entry
        self._entry = tkinter.ttk.Entry(self._frame)
        self._entry.insert(0, initial_value)
        
        # Create filter button
        self._button = tkinter.ttk.Button(
            master=self._frame,
            text="Update Filter",
            command=self._on_button_click
        )
        
        # Attach right-click menu if requested
        if attach_right_click_menu:
            self._attach_right_click_menu(self._entry)
        
        # Bind events
        self._entry.bind("<Return>", self._on_entry_return)
        
        # Store escape binding for later removal
        self._escape_binding: Optional[str] = None
        
        # Set up escape binding if we have an initial filter
        if initial_value and on_escape_clear:
            self._bind_escape_key()
    
    @property
    def frame(self) -> tkinter.ttk.Frame:
        """Get the containing frame."""
        return self._frame
    
    @property
    def entry(self) -> tkinter.ttk.Entry:
        """Get the search entry field."""
        return self._entry
    
    @property
    def button(self) -> tkinter.ttk.Button:
        """Get the filter button."""
        return self._button
    
    @property
    def value(self) -> str:
        """Get the current filter value."""
        return self._entry.get()
    
    def pack(self, **kwargs) -> None:
        """Pack the widget frame."""
        self._entry.pack(side=tkinter.LEFT)
        self._button.pack(side=tkinter.RIGHT)
        self._frame.pack(**kwargs)
    
    def clear(self) -> None:
        """Clear the search field."""
        self._entry.delete(0, "end")
        self._on_filter_applied("")
    
    def set_value(self, value: str) -> None:
        """Set the search field value.
        
        Args:
            value: The new value to set
        """
        self._entry.delete(0, "end")
        self._entry.insert(0, value)
    
    def disable(self) -> None:
        """Disable the search widget."""
        self._entry.configure(state=tkinter.DISABLED)
        self._button.configure(state=tkinter.DISABLED)
    
    def enable(self) -> None:
        """Enable the search widget."""
        self._entry.configure(state=tkinter.NORMAL)
        self._button.configure(state=tkinter.NORMAL)
    
    def _on_button_click(self) -> None:
        """Handle button click."""
        self._on_filter_applied(self._entry.get())
    
    def _on_entry_return(self, event=None) -> None:
        """Handle Return key press in entry field."""
        self._on_filter_applied(self._entry.get())
    
    def _on_filter_applied(self, filter_text: str) -> None:
        """Handle filter being applied.
        
        Args:
            filter_text: The new filter text
        """
        if self._filter_value != filter_text:
            # Unbind previous escape handler if any
            if self._escape_binding:
                try:
                    self._frame.winfo_toplevel().unbind("<Escape>")
                except tkinter.TclError:
                    pass
                self._escape_binding = None
            
            self._filter_value = filter_text
            
            # Bind escape to clear if we have a filter
            if filter_text and self._on_escape_clear:
                self._bind_escape_key()
            
            # Call the callback
            if self._on_filter_change:
                self._on_filter_change(filter_text)
    
    def _on_escape_pressed(self, event=None) -> None:
        """Handle Escape key press."""
        self.clear()
    
    def _bind_escape_key(self) -> None:
        """Bind the Escape key to clear the search field."""
        root = self._frame.winfo_toplevel()
        self._escape_binding = root.bind("<Escape>", self._on_escape_pressed)
    
    @staticmethod
    def _attach_right_click_menu(entry_widget: tkinter.ttk.Entry) -> None:
        """Attach a right-click context menu to an entry widget.
        
        Args:
            entry_widget: A tkinter Entry widget to attach the menu to
        """
        rclick_menu = tk_extra_widgets.RightClickMenu(entry_widget)
        entry_widget.bind("<3>", rclick_menu)
