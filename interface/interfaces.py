"""Protocol interfaces for UI components.

This module defines Protocol interfaces for UI-related operations,
enabling dependency injection and testing without actual UI components.

These protocols follow the structural subtyping approach where any
class that implements the required methods is considered a valid
implementation, without explicit inheritance.
"""

from typing import Protocol, runtime_checkable, Optional, Any, Callable


@runtime_checkable
class MessageBoxProtocol(Protocol):
    """Protocol for message box operations.
    
    Defines the interface for showing message dialogs to the user.
    Implementations can wrap tkinter.messagebox or custom dialogs.
    """
    
    def showinfo(self, title: str, message: str) -> None:
        """Show an information message box.
        
        Args:
            title: Dialog title
            message: Message to display
        """
        ...
    
    def showwarning(self, title: str, message: str) -> None:
        """Show a warning message box.
        
        Args:
            title: Dialog title
            message: Message to display
        """
        ...
    
    def showerror(self, title: str, message: str) -> None:
        """Show an error message box.
        
        Args:
            title: Dialog title
            message: Message to display
        """
        ...
    
    def askyesno(self, title: str, message: str) -> bool:
        """Show a yes/no dialog.
        
        Args:
            title: Dialog title
            message: Question to ask
            
        Returns:
            True if user clicked Yes, False otherwise
        """
        ...
    
    def askokcancel(self, title: str, message: str) -> bool:
        """Show an ok/cancel dialog.
        
        Args:
            title: Dialog title
            message: Message to display
            
        Returns:
            True if user clicked OK, False otherwise
        """
        ...
    
    def askyesnocancel(self, title: str, message: str) -> Optional[bool]:
        """Show a yes/no/cancel dialog.
        
        Args:
            title: Dialog title
            message: Question to ask
            
        Returns:
            True for Yes, False for No, None for Cancel
        """
        ...


@runtime_checkable
class FileDialogProtocol(Protocol):
    """Protocol for file dialog operations.
    
    Defines the interface for file and directory selection dialogs.
    Implementations can wrap tkinter.filedialog or custom dialogs.
    """
    
    def askdirectory(
        self,
        title: str = "Select Directory",
        initialdir: Optional[str] = None
    ) -> str:
        """Show a directory selection dialog.
        
        Args:
            title: Dialog title
            initialdir: Starting directory
            
        Returns:
            Selected directory path or empty string if cancelled
        """
        ...
    
    def askopenfilename(
        self,
        title: str = "Open File",
        initialdir: Optional[str] = None,
        filetypes: Optional[list[tuple[str, str]]] = None
    ) -> str:
        """Show an open file dialog.
        
        Args:
            title: Dialog title
            initialdir: Starting directory
            filetypes: List of (description, pattern) tuples
            
        Returns:
            Selected file path or empty string if cancelled
        """
        ...
    
    def asksaveasfilename(
        self,
        title: str = "Save File",
        initialdir: Optional[str] = None,
        defaultextension: str = "",
        filetypes: Optional[list[tuple[str, str]]] = None
    ) -> str:
        """Show a save file dialog.
        
        Args:
            title: Dialog title
            initialdir: Starting directory
            defaultextension: Default file extension
            filetypes: List of (description, pattern) tuples
            
        Returns:
            Selected file path or empty string if cancelled
        """
        ...
    
    def askopenfilenames(
        self,
        title: str = "Open Files",
        initialdir: Optional[str] = None,
        filetypes: Optional[list[tuple[str, str]]] = None
    ) -> tuple[str, ...]:
        """Show an open files dialog (multiple selection).
        
        Args:
            title: Dialog title
            initialdir: Starting directory
            filetypes: List of (description, pattern) tuples
            
        Returns:
            Tuple of selected file paths or empty tuple if cancelled
        """
        ...


@runtime_checkable
class WidgetProtocol(Protocol):
    """Protocol for UI widget operations.
    
    Defines the basic interface for tkinter-like widgets.
    """
    
    def pack(self, **kwargs) -> None:
        """Pack the widget using the pack geometry manager.
        
        Args:
            **kwargs: Pack options (side, fill, expand, etc.)
        """
        ...
    
    def grid(self, **kwargs) -> None:
        """Grid the widget using the grid geometry manager.
        
        Args:
            **kwargs: Grid options (row, column, sticky, etc.)
        """
        ...
    
    def destroy(self) -> None:
        """Destroy the widget."""
        ...
    
    def update(self) -> None:
        """Update the widget display."""
        ...
    
    def update_idletasks(self) -> None:
        """Update idle tasks without processing events."""
        ...


@runtime_checkable
class TkinterProtocol(Protocol):
    """Protocol for Tkinter root window operations.
    
    Defines the interface for the main application window.
    Implementations can wrap tkinter.Tk or custom window classes.
    """
    
    def title(self, title: str) -> None:
        """Set window title.
        
        Args:
            title: Window title text
        """
        ...
    
    def mainloop(self) -> None:
        """Start the main event loop."""
        ...
    
    def after(self, ms: int, func: Callable) -> str:
        """Schedule a function to run after a delay.
        
        Args:
            ms: Delay in milliseconds
            func: Function to call
            
        Returns:
            Timer ID for cancellation
        """
        ...
    
    def after_cancel(self, timer_id: str) -> None:
        """Cancel a scheduled function.
        
        Args:
            timer_id: Timer ID returned by after()
        """
        ...
    
    def withdraw(self) -> None:
        """Withdraw (hide) the window."""
        ...
    
    def deiconify(self) -> None:
        """Show the window after withdrawal."""
        ...
    
    def destroy(self) -> None:
        """Destroy the window."""
        ...
    
    def update(self) -> None:
        """Process pending events."""
        ...


@runtime_checkable
class OverlayProtocol(Protocol):
    """Protocol for overlay widgets.
    
    Defines the interface for overlay/loading screens.
    """
    
    def make_overlay(self, parent: Any, text: str) -> None:
        """Create and show the overlay.
        
        Args:
            parent: Parent widget
            text: Text to display on overlay
        """
        ...
    
    def update_overlay(self, parent: Any, text: str) -> None:
        """Update the overlay text.
        
        Args:
            parent: Parent widget
            text: New text to display
        """
        ...
    
    def destroy_overlay(self) -> None:
        """Destroy the overlay."""
        ...


@runtime_checkable
class VariableProtocol(Protocol):
    """Protocol for tkinter variable types.
    
    Defines the interface for StringVar, IntVar, BooleanVar, etc.
    """
    
    def get(self) -> Any:
        """Get the variable value.
        
        Returns:
            The current value
        """
        ...
    
    def set(self, value: Any) -> None:
        """Set the variable value.
        
        Args:
            value: New value to set
        """
        ...


@runtime_checkable
class EntryWidgetProtocol(Protocol):
    """Protocol for entry widget operations.
    
    Defines the interface for text entry widgets.
    """
    
    def get(self) -> str:
        """Get the current text.
        
        Returns:
            Current text content
        """
        ...
    
    def insert(self, index: int, text: str) -> None:
        """Insert text at position.
        
        Args:
            index: Position to insert at
            text: Text to insert
        """
        ...
    
    def delete(self, start: int, end: Optional[int] = None) -> None:
        """Delete text from the entry.
        
        Args:
            start: Start position
            end: End position (or None for end of text)
        """
        ...
    
    def config(self, **kwargs) -> None:
        """Configure widget options.
        
        Args:
            **kwargs: Configuration options
        """
        ...


@runtime_checkable
class ListboxProtocol(Protocol):
    """Protocol for listbox widget operations.
    
    Defines the interface for list selection widgets.
    """
    
    def get(self, start: int, end: Optional[int] = None) -> tuple[str, ...]:
        """Get items from the listbox.
        
        Args:
            start: Start index
            end: End index (or None for single item)
            
        Returns:
            Tuple of item strings
        """
        ...
    
    def curselection(self) -> tuple[int, ...]:
        """Get currently selected indices.
        
        Returns:
            Tuple of selected indices
        """
        ...
    
    def insert(self, index: int, *items: str) -> None:
        """Insert items at position.
        
        Args:
            index: Position to insert at
            *items: Items to insert
        """
        ...
    
    def delete(self, start: int, end: Optional[int] = None) -> None:
        """Delete items from the listbox.
        
        Args:
            start: Start index
            end: End index
        """
        ...
    
    def size(self) -> int:
        """Get the number of items.
        
        Returns:
            Number of items in listbox
        """
        ...
