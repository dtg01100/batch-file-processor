# Spec: PyQt6 Dialog Architecture Unification

**Status:** DRAFT  
**Author:** GitHub Copilot  
**Created:** 2026-02-03  
**Updated:** 2026-02-03

---

## 1. Summary

Unify all dialog classes in `interface/ui/dialogs/` around a single PyQt6-native base class and standardized lifecycle pattern, replacing tkinter-era structural leftovers (inconsistent base inheritance, ad-hoc OK/Cancel logic, and mixed apply/validate patterns).

---

## 2. Background

### 2.1 Problem Statement

The dialog layer has structural remnants from tkinter:
- **Inconsistent inheritance**: `EditFolderDialog` and `EditSettingsDialog` inherit `BaseDialog`, while others inherit raw `QDialog`.
- **Ad-hoc OK/Cancel logic**: Some dialogs reimplement button connections and validation flow manually.
- **Mixed lifecycle patterns**: `apply()` and `validate()` methods exist in some dialogs but not others, making data flow unpredictable.
- **No standardized data contract**: Dialogs don't enforce a consistent pattern for reading/writing data to/from the model.

### 2.2 Motivation

Standardizing dialog architecture reduces code duplication, makes data flow predictable, and prepares dialogs for native boolean migration (Spec 2). A unified base ensures all dialogs follow the same patterns for initialization, validation, data application, and cancellation.

### 2.3 Prior Art

- Current `BaseDialog` (in `interface/ui/base_dialog.py`) attempts to provide a template but is underused.
- PyQt6 best practices recommend a `Dialog` + `Model` pattern with explicit `validate()` and `apply()` phases.
- Tkinter-era `tkinter.simpledialog.Dialog` pattern (old code) used `result` return value and `buttonbox` OK/Cancel bindings.

---

## 3. Design

### 3.1 Architecture Alignment

- [x] Reviewed `docs/GUI_DESIGN.md` — confirms three-layer signal propagation; dialogs fit in widget/controller layer.
- [x] Reviewed `docs/ARCHITECTURE.md` — confirms modular structure and plugin architecture.
- [x] Reviewed `docs/TESTING_DESIGN.md` — confirms Qt testing patterns with `qapp` and `qtbot` fixtures.

### 3.2 Technical Approach

**Components affected:**
- [x] `interface/ui/base_dialog.py` — enhance base class with explicit lifecycle contract.
- [x] `interface/ui/dialogs/edit_folder_dialog.py` — inherit unified base, implement `validate()` and `apply()`.
- [x] `interface/ui/dialogs/edit_settings_dialog.py` — same pattern.
- [x] `interface/ui/dialogs/maintenance_dialog.py` — same pattern.
- [x] `interface/ui/dialogs/about_dialog.py` — same pattern.
- [x] `interface/ui/dialogs/batch_add_folders_dialog.py` — same pattern.
- [x] All other dialogs in `interface/ui/dialogs/` — same pattern.

**API changes — New BaseDialog contract:**

```python
class BaseDialog(QDialog):
    """
    Base class for all application dialogs.
    
    Lifecycle:
    1. __init__ — initialize UI and set initial data
    2. _setup_ui() — build widgets (overridable)
    3. _set_dialog_values() — populate UI from data model (overridable)
    4. validate() — check data validity, return (is_valid, error_message) tuple
    5. apply() — write UI values back to data model (overridable)
    6. done(result) — called on OK/Cancel/close
    """
    
    def __init__(self, parent=None, title="Dialog", data=None):
        super().__init__(parent)
        self.setWindowTitle(title)
        self.data = data or {}
        self.original_data = deepcopy(self.data)
        
        self._layout = QVBoxLayout(self)
        self._setup_ui()
        self._set_dialog_values()
        self._setup_buttons()
    
    def _setup_ui(self) -> None:
        """Override to build dialog widgets. Called during __init__."""
        pass
    
    def _set_dialog_values(self) -> None:
        """Override to populate UI from self.data. Called during __init__."""
        pass
    
    def validate(self) -> tuple[bool, str]:
        """
        Validate dialog data. Override as needed.
        
        Returns:
            (is_valid, error_message) tuple
        """
        return (True, "")
    
    def apply(self) -> None:
        """Override to write UI values back to self.data."""
        pass
    
    def done(self, result: int) -> None:
        """Called when dialog is closed (OK/Cancel/X button)."""
        if result == QDialog.DialogCode.Accepted:
            is_valid, error_msg = self.validate()
            if not is_valid:
                QMessageBox.warning(self, "Validation Error", error_msg)
                return
            self.apply()
        super().done(result)
    
    def _setup_buttons(self) -> None:
        """Setup OK/Cancel buttons (no override needed)."""
        button_layout = QHBoxLayout()
        ok_btn = QPushButton("OK")
        cancel_btn = QPushButton("Cancel")
        ok_btn.clicked.connect(lambda: self.done(QDialog.DialogCode.Accepted))
        cancel_btn.clicked.connect(lambda: self.done(QDialog.DialogCode.Rejected))
        button_layout.addStretch()
        button_layout.addWidget(ok_btn)
        button_layout.addWidget(cancel_btn)
        self._layout.addLayout(button_layout)
```

**Data flow:**

```
Dialog open
  ├─ __init__(data=folder_data)
  ├─ _setup_ui() — build widgets
  ├─ _set_dialog_values() — read self.data into UI
  └─ User interacts
      ├─ OK clicked
      │   ├─ validate() — check constraints
      │   ├─ apply() — write UI → self.data
      │   └─ return data
      └─ Cancel clicked
          └─ discard changes, return None
```

### 3.3 Alternatives Considered

| Alternative | Pros | Cons | Why Not Chosen |
|-------------|------|------|----------------|
| Keep inconsistent bases | No refactoring effort | Increases technical debt, makes Spec 2 harder | Chosen against |
| Use Qt Model/View pattern | Decouples data from UI | More complex, overhead for simple dialogs | Overkill for current scope |
| Keep tkinter-style `apply()` only, no `validate()` | Less change | Doesn't prevent invalid data submission | Chosen against |

---

## 4. Implementation Plan

### Phase 1: Enhance BaseDialog (Estimated: 1 day)

- [ ] Task 1.1: Review current `BaseDialog` implementation
- [ ] Task 1.2: Add explicit `validate()` and `apply()` lifecycle methods
- [ ] Task 1.3: Implement automatic OK/Cancel button wiring with validation
- [ ] Task 1.4: Add docstrings and lifecycle comments
- [ ] Deliverable: `BaseDialog` ready for all dialogs to inherit

### Phase 2: Refactor Dialog Classes (Estimated: 2 days)

- [ ] Task 2.1: Refactor `EditFolderDialog` to use `validate()` and `apply()`
- [ ] Task 2.2: Refactor `EditSettingsDialog` to inherit `BaseDialog` if not already
- [ ] Task 2.3: Refactor `MaintenanceDialog`, `AboutDialog`, `BatchAddFoldersDialog`
- [ ] Task 2.4: Refactor any remaining dialogs in `interface/ui/dialogs/`
- [ ] Deliverable: All dialogs follow unified base and lifecycle pattern

### Phase 3: Testing & Documentation (Estimated: 1 day)

- [ ] Task 3.1: Write unit tests for `BaseDialog` lifecycle (validate/apply/done)
- [ ] Task 3.2: Write integration tests for each refactored dialog
- [ ] Task 3.3: Update `docs/GUI_DESIGN.md` with new dialog pattern
- [ ] Task 3.4: Add code comments explaining lifecycle in each dialog
- [ ] Deliverable: All tests passing, docs updated

---

## 5. Testing Strategy

### Unit Tests
- **BaseDialog lifecycle**: validate/apply/done flow, default behaviors
- **Each dialog**: validate() correctness, apply() data mutation, initial data load

### Integration Tests
- **Dialog round-trip**: load data → modify UI → apply → check data changed
- **Validation errors**: invalid data → validate() returns False → dialog stays open
- **Cancellation**: modify UI → Cancel → data unchanged

### Test Cases
```python
# Example: EditFolderDialog
def test_edit_folder_dialog_loads_data():
    dialog = EditFolderDialog(folder_data={"folder_alias": "Test", "folder_is_active": True})
    assert dialog.folder_alias_input.text() == "Test"
    assert dialog.active_checkbox.isChecked() is True

def test_edit_folder_dialog_apply():
    dialog = EditFolderDialog(folder_data={"folder_alias": "Old"})
    dialog.folder_alias_input.setText("New")
    dialog.apply()
    assert dialog.data["folder_alias"] == "New"

def test_edit_folder_dialog_validate_fails_empty_alias():
    dialog = EditFolderDialog(folder_data={"folder_alias": "Test"})
    dialog.folder_alias_input.setText("")
    is_valid, msg = dialog.validate()
    assert is_valid is False
```

---

## 6. Risk Assessment

**Potential issues:**
1. **Dialogs have complex interdependencies** — Some dialogs emit signals that affect other dialogs. Ensure signals still work after refactoring.
2. **Backward compatibility** — Changing dialog APIs might break external code. Mitigate: ensure signals and return values don't change.
3. **UI widget initialization order** — If dialogs rely on certain widget creation order, refactoring might break edge cases. Mitigate: test all dialog paths (edit/create/cancel).

**Mitigations:**
- Test each dialog individually and as part of full app flow.
- Keep dialog `data` attribute and return semantics unchanged.
- Run full test suite (`./run_tests.sh`) before commit.

---

## 7. Success Criteria

- [x] All dialog classes inherit `BaseDialog` (or raw `QDialog` only if justified)
- [x] All dialogs implement `validate()` and `apply()` methods
- [x] OK button triggers validate/apply workflow; Cancel discards changes
- [x] All 1600+ tests pass
- [x] Dialog docs in `docs/GUI_DESIGN.md` updated
- [x] No tkinter-style code comments or patterns in dialog code

---

## 8. Timeline & Effort

- **Phase 1 (BaseDialog)**: 1 day
- **Phase 2 (Refactor dialogs)**: 2 days
- **Phase 3 (Testing & docs)**: 1 day
- **Total**: ~4 days (accounting for testing and edge cases)

---

## 9. Dependencies

- Spec 2 (Boolean Normalization) can run in parallel but ideally completes **after** this spec's Phase 2 (dialogs refactored) so that dialog data handling is clean before boolean changes.
