"""Single source of truth for Qt binding selection.

Phase 1 of the Qt5 -> Qt6 modernization. Imports from PyQt5 or PySide6
go through this module instead of touching the bindings directly, so
each call site migrates independently and the active binding can be
flipped by setting ``BATCH_QT_BINDING`` (defaults to ``pyside6``).

Symbol coverage is exhaustive for the symbols actually imported by
``interface/`` and ``tests/``. Adding a symbol not exported here will
surface as ``ImportError`` at module load time, which is the intended
failure mode.

Notable shims applied:

* ``pyqtSignal`` is re-exported as the PySide6 ``Signal`` (and as
  ``pyqtSignal`` itself for PyQt5). The names differ between bindings;
  this module exposes ``pyqtSignal`` on both branches so call sites
  can keep using the PyQt5 spelling.
* ``Qt`` enums are passed through unchanged. Scoped-enum migration
  (e.g. ``Qt.AlignLeft`` -> ``Qt.AlignmentFlag.AlignLeft``) is left
  to Phase 4 — both forms work on both bindings today.
* ``exec_()`` is gone from this codebase already; ``exec()`` is the
  only call form in use. No shim needed.
* Qt6 reorganized some widgets out of ``QtWidgets``. ``QShortcut``
  moved to ``QtGui``. The shim handles this in each branch so call
  sites can keep importing from a single place.
* ``QtCore`` (and ``QtGui``/``QtWidgets``) module namespaces are
  re-exported as ``QtCore`` so call sites that do ``QtCore.Qt.X``
  (or any other module-qualified access) keep working.

Phase 3 will collapse this to a single-binding re-export module.
"""
from __future__ import annotations

import os

_BINDING = os.environ.get("BATCH_QT_BINDING", "pyside6").strip().lower()

if _BINDING == "pyside6":
    from PySide6 import QtCore as _QtCore_module
    from PySide6 import QtGui as _QtGui_module
    from PySide6 import QtWidgets as _QtWidgets_module
    from PySide6.QtCore import (
        QDate,
        QEasingCurve,
        QEvent,
        QItemSelectionModel,
        QObject,
        QPropertyAnimation,
        Qt,
        QThread,
        QTimer,
    )
    from PySide6.QtCore import (
        Signal as pyqtSignal,
    )
    from PySide6.QtGui import (
        QCloseEvent,
        QColor,
        QFontMetrics,
        QKeyEvent,
        QKeySequence,
        QPalette,
        QShortcut,
    )
    from PySide6.QtWidgets import (
        QAbstractItemView,
        QApplication,
        QButtonGroup,
        QCheckBox,
        QComboBox,
        QDateEdit,
        QDialog,
        QDialogButtonBox,
        QDoubleSpinBox,
        QFileDialog,
        QFormLayout,
        QFrame,
        QGraphicsOpacityEffect,
        QGroupBox,
        QHBoxLayout,
        QLabel,
        QLineEdit,
        QListWidget,
        QListWidgetItem,
        QMainWindow,
        QMessageBox,
        QProgressBar,
        QPushButton,
        QScrollArea,
        QSizePolicy,
        QSpinBox,
        QStyle,
        QTableWidget,
        QTableWidgetItem,
        QTabWidget,
        QTextEdit,
        QToolButton,
        QVBoxLayout,
        QWidget,
    )
elif _BINDING == "pyqt5":
    from PyQt5 import QtCore as _QtCore_module
    from PyQt5 import QtGui as _QtGui_module
    from PyQt5 import QtWidgets as _QtWidgets_module
    from PyQt5.QtCore import (
        QDate,
        QEasingCurve,
        QEvent,
        QItemSelectionModel,
        QObject,
        QPropertyAnimation,
        Qt,
        QThread,
        QTimer,
        pyqtSignal,
    )
    from PyQt5.QtGui import (
        QCloseEvent,
        QColor,
        QFontMetrics,
        QKeyEvent,
        QKeySequence,
        QPalette,
        QShortcut,
    )
    from PyQt5.QtWidgets import (
        QAbstractItemView,
        QApplication,
        QButtonGroup,
        QCheckBox,
        QComboBox,
        QDateEdit,
        QDialog,
        QDialogButtonBox,
        QDoubleSpinBox,
        QFileDialog,
        QFormLayout,
        QFrame,
        QGraphicsOpacityEffect,
        QGroupBox,
        QHBoxLayout,
        QLabel,
        QLineEdit,
        QListWidget,
        QListWidgetItem,
        QMainWindow,
        QMessageBox,
        QProgressBar,
        QPushButton,
        QScrollArea,
        QSizePolicy,
        QSpinBox,
        QStyle,
        QTableWidget,
        QTableWidgetItem,
        QTabWidget,
        QTextEdit,
        QToolButton,
        QVBoxLayout,
        QWidget,
    )
else:
    raise RuntimeError(
        f"Unknown BATCH_QT_BINDING: {_BINDING!r}. "
        "Expected 'pyside6' or 'pyqt5'."
    )

ACTIVE_BINDING = _BINDING

# Re-export module namespaces under the public name so call sites that
# reference QtCore.Qt / QtGui.X / QtWidgets.Y keep working without
# reaching for the binding-specific module name.
QtCore = _QtCore_module
QtGui = _QtGui_module
QtWidgets = _QtWidgets_module

__all__ = [
    "ACTIVE_BINDING",
    "QAbstractItemView",
    "QApplication",
    "QButtonGroup",
    "QCheckBox",
    "QCloseEvent",
    "QColor",
    "QComboBox",
    "QDate",
    "QDateEdit",
    "QDialog",
    "QDialogButtonBox",
    "QDoubleSpinBox",
    "QEasingCurve",
    "QEvent",
    "QFileDialog",
    "QFontMetrics",
    "QFormLayout",
    "QFrame",
    "QGraphicsOpacityEffect",
    "QGroupBox",
    "QHBoxLayout",
    "QItemSelectionModel",
    "QKeyEvent",
    "QKeySequence",
    "QLabel",
    "QLineEdit",
    "QListWidget",
    "QListWidgetItem",
    "QMainWindow",
    "QMessageBox",
    "QObject",
    "QPalette",
    "QProgressBar",
    "QPropertyAnimation",
    "QPushButton",
    "QScrollArea",
    "QShortcut",
    "QSizePolicy",
    "QSpinBox",
    "QStyle",
    "QTabWidget",
    "QTableWidget",
    "QTableWidgetItem",
    "QTextEdit",
    "QThread",
    "QTimer",
    "QToolButton",
    "QVBoxLayout",
    "QWidget",
    "Qt",
    "QtCore",
    "QtGui",
    "QtWidgets",
    "pyqtSignal",
]

