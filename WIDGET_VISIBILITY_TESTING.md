# Widget Visibility Testing in PyQt Applications

This document explains various techniques for testing widget visibility in PyQt applications, particularly in the context of the batch file processor application.

## Methods for Testing Widget Visibility

### 1. Basic Visibility Check
```python
widget.isVisible()  # Returns True if widget is visible, False otherwise
```

The `isVisible()` method checks if a widget is currently visible to the user. A widget is considered visible if it and all its parent widgets are shown.

### 2. Using Qt Testing Framework
```python
from pytestqt import qtbot

def test_widget_visibility(qtbot):
    widget = SomeWidget()
    qtbot.addWidget(widget)
    
    # Show the widget
    widget.show()
    qtbot.wait(10)  # Brief pause to allow rendering
    
    # Check visibility
    assert widget.isVisible()
```

### 3. Visibility Under Different Conditions
```python
def test_visibility_conditions(qtbot):
    widget = SomeWidget()
    qtbot.addWidget(widget)
    
    # Initially hidden
    assert not widget.isVisible()
    
    # After showing
    widget.show()
    assert widget.isVisible()
    
    # After hiding
    widget.hide()
    assert not widget.isVisible()
```

### 4. Child Widget Visibility
```python
def test_child_widget_visibility(qtbot):
    parent = ParentWidget()
    qtbot.addWidget(parent)
    parent.show()
    
    # Check if child widgets are visible
    assert parent.child_widget.isVisible()
    
    # Find widgets by type
    child_buttons = parent.findChildren(QPushButton)
    for btn in child_buttons:
        assert btn.isVisible()
```

### 5. Tab Widget Visibility
```python
def test_tab_visibility(qtbot):
    tab_widget = QTabWidget()
    qtbot.addWidget(tab_widget)
    tab_widget.show()
    
    # Tabs themselves are visible
    assert tab_widget.isVisible()
    
    # Check if current tab's content is visible
    current_tab = tab_widget.currentWidget()
    if current_tab:
        assert current_tab.isVisible()
```

## Specific Techniques Used in Batch File Processor Tests

### Button Panel Visibility
```python
def test_button_panel_widgets_are_visible(self, qtbot):
    panel = ButtonPanel()
    qtbot.addWidget(panel)
    panel.show()
    qtbot.wait(10)
    
    # Check all buttons are visible
    assert panel._add_folder_btn.isVisible()
    assert panel._process_btn.isVisible()
    # ... etc
```

### Dialog Widget Visibility
```python
def test_edit_folder_dialog_widgets_are_visible(self, qtbot):
    dialog = EditFolderDialog(...)
    qtbot.addWidget(dialog)
    dialog.show()
    qtbot.wait(10)
    
    # Check key widgets are visible
    assert dialog._tabs.isVisible()
    assert dialog._alias_field.isVisible()
    
    # Find and check specific buttons
    buttons = dialog._general_tab.findChildren(QPushButton)
    show_path_button = None
    for btn in buttons:
        if btn.text() == "Show Folder Path":
            show_path_button = btn
            break
    assert show_path_button.isVisible()
```

## Advanced Visibility Checks

### 1. Geometry-Based Visibility
```python
def is_widget_on_screen(widget):
    """Check if widget is positioned where it could be visible."""
    if not widget.isVisible():
        return False
    
    # Get widget geometry
    rect = widget.geometry()
    
    # Check if it's within screen bounds
    screen = widget.screen()
    screen_rect = screen.geometry()
    
    return screen_rect.intersects(rect)
```

### 2. Opacity and Style Checks
```python
def is_widget_visually_visible(widget):
    """Check if widget is visible considering opacity and styles."""
    if not widget.isVisible():
        return False
    
    # Check opacity (0.0 means completely transparent)
    if widget.windowOpacity() == 0.0:
        return False
    
    # Additional style checks could go here
    
    return True
```

### 3. Parent Chain Visibility
```python
def is_widget_in_visible_chain(widget):
    """Check if widget and all its parents are visible."""
    current = widget
    while current:
        if not current.isVisible():
            return False
        current = current.parent()
    return True
```

## Best Practices for Visibility Testing

1. **Always show the widget first**: Use `widget.show()` before testing visibility
2. **Allow rendering time**: Use `qtbot.wait(10)` to allow UI to render
3. **Test parent-child relationships**: Ensure parent widgets are visible before child widgets
4. **Clean up properly**: Use `qtbot.addWidget()` and `widget.deleteLater()` for proper cleanup
5. **Use findChildren()**: For finding specific child widgets by type or property
6. **Consider timing**: Some visibility changes happen asynchronously

## Common Pitfalls

- Testing visibility before showing the widget
- Forgetting that visibility is inherited from parent widgets
- Not accounting for tabbed interfaces where only current tab content is visible
- Assuming all child widgets become visible when parent is shown (some might be disabled or hidden individually)

## Running Visibility Tests

To run the visibility tests in the batch file processor application:

```bash
python -m pytest tests/ui/test_button_resilience.py::TestWidgetVisibility -v
```

This will run all the visibility-specific tests we've implemented.