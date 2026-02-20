import unittest
from dialog import Dialog
from interface.qt.dialogs.edit_folders_dialog import EditFoldersDialog

class TestLayoutComparison(unittest.TestCase):
    def test_widget_hierarchy_consistency(self):
        # Capture Tkinter hierarchy
        tk_dialog = Dialog(None, "test")
        tk_hierarchy = self._capture_hierarchy(tk_dialog)
        
        # Capture Qt hierarchy
        qt_dialog = EditFoldersDialog()
        qt_hierarchy = self._capture_hierarchy(qt_dialog)
        
        # Compare counts
        self.assertEqual(len(tk_hierarchy), len(qt_hierarchy), 
                        "Widget count mismatch between implementations")
        
        # Compare types
        tk_types = self._get_widget_types(tk_hierarchy)
        qt_types = self._get_widget_types(qt_hierarchy)
        self.assertEqual(tk_types, qt_types, 
                        "Widget type mismatch between implementations")
        
        # Special case: EDI config visibility
        self.assertEqual(self._is_edi_visible(tk_hierarchy), 
                        self._is_edi_visible(qt_hierarchy),
                        "EDI config visibility differs between implementations")

    def _capture_hierarchy(self, dialog):
        """Capture widget hierarchy from dialog implementation."""
        hierarchy = []
        for widget in self._traverse_widgets(dialog):
            hierarchy.append({
                'type': type(widget).__name__,
                'children': self._get_children(widget)
            })
        return hierarchy

    def _traverse_widgets(self, widget):
        """Recursively traverse widget tree."""
        children = []
        for child in widget.winfo_children():
            children.append(child)
            children.extend(self._traverse_widgets(child))
        return [widget] + children

    def _get_children(self, widget):
        """Get direct children of widget."""
        return widget.winfo_children()

    def _get_widget_types(self, hierarchy):
        """Extract widget types from hierarchy."""
        return [item['type'] for item in hierarchy]

    def _is_edi_visible(self, hierarchy):
        """Check EDI configuration section visibility."""
        for item in hierarchy:
            if 'EDI' in item['type'] or 'config' in item['type'].lower():
                return True
        return False

if __name__ == '__main__':
    unittest.main()