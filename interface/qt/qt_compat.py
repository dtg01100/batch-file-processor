"""Single source of truth for Qt symbols.

Phase 3 of the Qt5 -> Qt6 modernization. After dropping PyQt5
support, this module became a thin re-export hub over PySide6.
Future Qt-binding swaps are still easy: replace the import
block below with the new binding's re-exports and update
``ACTIVE_BINDING``.

Symbol coverage is exhaustive for what the codebase actually
imports. Adding a symbol not exported here surfaces as
``ImportError`` at module load time, which is the intended
failure mode.

Notes:

* ``pyqtSignal`` is re-exported as PySide6's ``Signal`` so call
  sites that used the PyQt5 spelling keep working. The PyQt5
  binding used the same name; PySide6 renamed it.
* ``Qt`` enums are passed through unchanged. Scoped-enum
  migration (e.g. ``Qt.AlignLeft`` -> ``Qt.AlignmentFlag.AlignLeft``)
  is left as-is — both forms work on PySide6 today.
* ``exec_()`` was never used in this codebase; ``exec()`` is the
  only call form.
* Qt6 reorganized some widgets out of ``QtWidgets``. ``QShortcut``
  lives in ``QtGui`` in PySide6 (QtWidgets in PyQt5). The shim
  exposes it from the correct PySide6 module.
* Module namespaces ``QtCore`` / ``QtGui`` / ``QtWidgets`` are
  re-exported so call sites that do ``QtCore.Qt.X`` keep working.
"""
from __future__ import annotations

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
from PySide6.QtCore import (
    Slot as pyqtSlot,
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
    QSpacerItem,
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

ACTIVE_BINDING = "pyside6"

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
    "QSpacerItem",
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
    "pyqtSlot",
]
