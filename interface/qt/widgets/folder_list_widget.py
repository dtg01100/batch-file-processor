"""Folder list widget for displaying and managing folder configurations.

This module provides a Qt widget for displaying folders with inline status indicators
and action buttons for send, edit, enable/disable, and delete operations.

The widget creates a single scrollable list with each folder showing its active/inactive
status inline. Each folder row contains action buttons appropriate to its status.

Fuzzy matching via the ``thefuzz`` library is used to filter folders by alias
when a filter value is provided.
"""

from typing import Any, Callable, Dict, Iterator, List, Optional, Protocol

import thefuzz.process  # type: ignore
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QFontMetrics
from PyQt6.QtWidgets import (
    QFrame,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QScrollArea,
    QSizePolicy,
    QVBoxLayout,
    QWidget,
)

from core.utils.bool_utils import normalize_bool
from interface.qt.theme import Theme


class FolderTableProtocol(Protocol):
    """Protocol describing the expected interface for a folder data table.

    The table must support keyword-based lookups via :meth:`find` and return
    dictionaries containing at least the keys ``id``, ``alias``, and
    ``folder_is_active``.
    """

    def find(self, **kwargs: Any) -> Iterator[Dict[str, Any]]:
        """Return folders matching the given criteria.

        Args:
            **kwargs: Filter criteria, e.g. ``folder_is_active=True``.

        Returns:
            An iterator of folder dictionaries.
        """
        ...

    def count(self, **kwargs: Any) -> int:
        """Return the number of folders matching the given criteria.

        Args:
            **kwargs: Filter criteria.

        Returns:
            The matching folder count.
        """
        ...

    def find_one(self, **kwargs: Any) -> Optional[Dict[str, Any]]:
        """Return a single folder matching the given criteria, or ``None``.

        Args:
            **kwargs: Filter criteria.

        Returns:
            A folder dictionary or ``None``.
        """
        ...


class FolderListWidget(QWidget):
    """A widget displaying folders in a single list with inline status indicators.

    This widget creates a scrollable list of folders with each row showing the
    folder's active/inactive status inline.  Each folder has action buttons for
    common operations such as send, edit, enable/disable, and delete.

    The widget supports fuzzy filtering of folders by alias name using the
    ``thefuzz`` library with a score cutoff of 80.

    Args:
        parent: The parent widget.
        folders_table: The database table containing folder configurations.
        on_send: Callback for the *Send* button (receives folder ID).
        on_edit: Callback for the *Edit* button (receives folder ID).
        on_toggle: Callback for the *Enable/Disable* button (receives folder ID).
        on_delete: Callback for the *Delete* button (receives folder ID and alias).
        filter_value: Current filter value for fuzzy matching.  An empty
            string disables filtering.
        total_count_callback: Optional callback invoked with
            ``(filtered_count, total_count)`` after folders are loaded.

    Example::

        >>> def on_send(folder_id: int) -> None: ...
        >>> def on_edit(folder_id: int) -> None: ...
        >>> def on_toggle(folder_id: int) -> None: ...
        >>> def on_delete(folder_id: int, alias: str) -> None: ...
        >>>
        >>> widget = FolderListWidget(
        ...     parent=window,
        ...     folders_table=database.folders_table,
        ...     on_send=on_send,
        ...     on_edit=on_edit,
        ...     on_toggle=on_toggle,
        ...     on_delete=on_delete,
        ...     filter_value="",
        ... )
    """

    def __init__(
        self,
        parent: QWidget,
        folders_table: FolderTableProtocol,
        on_send: Callable[[int], None],
        on_edit: Callable[[int], None],
        on_toggle: Callable[[int], None],
        on_delete: Callable[[int, str], None],
        filter_value: str = "",
        total_count_callback: Optional[Callable[[int, int], None]] = None,
    ) -> None:
        super().__init__(parent)
        self._folders_table = folders_table
        self._on_send = on_send
        self._on_edit = on_edit
        self._on_toggle = on_toggle
        self._on_delete = on_delete
        self._filter_value = filter_value
        self._total_count_callback = total_count_callback
        self._row_widgets: Dict[int, QWidget] = {}
        self._folder_aliases: Dict[int, str] = {}
        self._scroll_layout: Optional[QVBoxLayout] = None
        self._scroll_area: Optional[QScrollArea] = None
        self._empty_label: Optional[QLabel] = None
        self._edit_button_min_width: int = 0

        self._build_widget()

    # ------------------------------------------------------------------
    # Widget construction
    # ------------------------------------------------------------------

    def _build_widget(self) -> None:
        """Build the complete folder list widget.

        All rows are created up front; the initial filter is applied via
        visibility so subsequent filter changes are just show/hide operations.
        """
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(Theme.SPACING_LG_INT)

        # Get all folders sorted by alias
        all_folders: List[Dict[str, Any]] = list(
            self._folders_table.find(order_by="alias")
        )

        # Build column with ALL folders (visibility controlled by filter)
        folder_column = self._build_column(
            title="Folders",
            folder_list=all_folders,
        )

        main_layout.addWidget(folder_column, stretch=1)

        # Apply initial filter via visibility
        self.apply_filter(self._filter_value)

    def _build_column(
        self,
        title: str,
        folder_list: List[Dict[str, Any]],
    ) -> QWidget:
        """Build a scrollable column for all folders.

        Args:
            title: The column header text (e.g. ``"Folders"``).
            folder_list: The filtered folders to display.

        Returns:
            A :class:`QWidget` containing the titled, scrollable column.
        """
        container = QWidget()
        container.setObjectName("card")
        container.setStyleSheet(
            f"""
            #card {{
                background-color: {Theme.CARD_BACKGROUND};
                border: 1px solid {Theme.CARD_BORDER};
                border-radius: {Theme.RADIUS_LG};
                padding: {Theme.SPACING_LG};
            }}
        """
        )
        container_layout = QVBoxLayout(container)
        container_layout.setContentsMargins(
            Theme.SPACING_LG_INT,
            Theme.SPACING_LG_INT,
            Theme.SPACING_LG_INT,
            Theme.SPACING_LG_INT,
        )
        container_layout.setSpacing(Theme.SPACING_MD_INT)

        # Modern header with enhanced typography
        header = QLabel(title)
        header.setAlignment(Qt.AlignmentFlag.AlignCenter)
        header.setStyleSheet(
            f"""
            font-size: {Theme.FONT_SIZE_XL};
            font-weight: 600;
            color: {Theme.TEXT_PRIMARY};
            padding-bottom: {Theme.SPACING_MD};
            letter-spacing: 0.25px;
        """
        )
        container_layout.addWidget(header)

        # Modern separator
        separator = QFrame()
        separator.setFrameShape(QFrame.Shape.HLine)
        separator.setFrameShadow(QFrame.Shadow.Plain)
        separator.setObjectName("separator")
        separator.setStyleSheet(
            f"""
            QFrame#separator {{
                background-color: {Theme.OUTLINE_VARIANT};
                border: none;
                height: 1px;
            }}
        """
        )
        container_layout.addWidget(separator)

        # Scroll area with modern styling
        scroll_area = QScrollArea()
        scroll_area.setWidgetResizable(True)
        scroll_area.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
        scroll_area.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
        scroll_area.setStyleSheet(
            """
            QScrollArea {
                border: none;
                background-color: transparent;
            }
        """
        )

        scroll_content = QWidget()
        scroll_layout = QVBoxLayout(scroll_content)
        scroll_layout.setContentsMargins(
            Theme.SPACING_SM_INT,
            Theme.SPACING_MD_INT,
            Theme.SPACING_SM_INT,
            Theme.SPACING_SM_INT,
        )
        scroll_layout.setSpacing(Theme.SPACING_SM_INT)

        if not folder_list:
            self._empty_label = QLabel(f"No {title}")
            self._empty_label.setStyleSheet(
                f"""
                color: {Theme.TEXT_TERTIARY};
                font-size: {Theme.FONT_SIZE_SM};
                font-style: italic;
            """
            )
            self._empty_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
            self._empty_label.setContentsMargins(
                Theme.SPACING_LG_INT,
                Theme.SPACING_XXL_INT,
                Theme.SPACING_LG_INT,
                Theme.SPACING_XXL_INT,
            )
            scroll_layout.addWidget(self._empty_label)
        else:
            # Create "no matches" label (hidden by default, shown when filter hides all)
            self._empty_label = QLabel("No matching folders")
            self._empty_label.setStyleSheet(
                f"""
                color: {Theme.TEXT_TERTIARY};
                font-size: {Theme.FONT_SIZE_SM};
                font-style: italic;
            """
            )
            self._empty_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
            self._empty_label.setContentsMargins(
                Theme.SPACING_LG_INT,
                Theme.SPACING_XXL_INT,
                Theme.SPACING_LG_INT,
                Theme.SPACING_XXL_INT,
            )
            self._empty_label.setVisible(False)
            scroll_layout.addWidget(self._empty_label)

        edit_button_min_width = self._calculate_edit_button_min_width(folder_list)
        self._edit_button_min_width = edit_button_min_width

        for folder in folder_list:
            row = self._build_folder_row(folder, edit_button_min_width)
            self._row_widgets[folder["id"]] = row
            self._folder_aliases[folder["id"]] = folder.get("alias", "")
            scroll_layout.addWidget(row)

        scroll_layout.addStretch(1)
        scroll_area.setWidget(scroll_content)
        self._scroll_layout = scroll_layout
        self._scroll_area = scroll_area
        container_layout.addWidget(scroll_area, stretch=1)

        return container

    def _build_folder_row(
        self,
        folder: Dict[str, Any],
        edit_button_min_width: int,
    ) -> QWidget:
        """Build a single folder row with status indicator and action buttons.

        Args:
            folder: A folder dictionary with ``id``, ``alias``, and ``folder_is_active`` keys.
            edit_button_min_width: Minimum width used for edit buttons in the list.

        Returns:
            A :class:`QWidget` representing the folder row.
        """
        row_widget = QWidget()
        row_widget.setObjectName("folderCard")
        row_widget.setStyleSheet(
            f"""
            #folderCard {{
                background-color: {Theme.CARD_SURFACE};
                border: 1px solid {Theme.CARD_BORDER};
                border-radius: {Theme.RADIUS_MD};
                padding: {Theme.SPACING_SM};
            }}
            #folderCard:hover {{
                background-color: {Theme.SURFACE_VARIANT};
                border-color: {Theme.PRIMARY};
            }}
        """
        )
        row_layout = QHBoxLayout(row_widget)
        row_layout.setContentsMargins(
            Theme.SPACING_SM_INT,
            Theme.SPACING_SM_INT,
            Theme.SPACING_SM_INT,
            Theme.SPACING_SM_INT,
        )
        row_layout.setSpacing(Theme.SPACING_SM_INT)

        folder_id: int = folder["id"]
        alias: str = folder["alias"]
        is_active: bool = normalize_bool(folder.get("folder_is_active"))

        # Status toggle button -- shows state and toggles on click
        toggle_symbol = "\u25cf" if is_active else "\u25cb"  # ● active, ○ inactive
        toggle_btn = QPushButton(toggle_symbol)
        toggle_btn.setFixedSize(36, 36)
        toggle_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        if is_active:
            toggle_btn.setToolTip("Active -- click to disable")
            toggle_btn.setAccessibleName(
                f"Disable folder {alias}" if alias else "Disable folder"
            )
            toggle_btn.setAccessibleDescription(
                f"Folder '{alias}' is active. Click to disable."
            )
            toggle_btn.setStyleSheet(
                f"""
                QPushButton {{
                    color: {Theme.PRIMARY};
                    background-color: transparent;
                    border: 2px solid {Theme.PRIMARY};
                    border-radius: 18px;
                    font-size: 20px;
                    font-weight: bold;
                    padding: 0;
                }}
                QPushButton:hover {{
                    background-color: {Theme.PRIMARY_CONTAINER};
                }}
                QPushButton:pressed {{
                    background-color: {Theme.SECONDARY_CONTAINER};
                }}
                """
            )
        else:
            toggle_btn.setToolTip("Inactive -- click to enable")
            toggle_btn.setAccessibleName(
                f"Enable folder {alias}" if alias else "Enable folder"
            )
            toggle_btn.setAccessibleDescription(
                f"Folder '{alias}' is inactive. Click to enable."
            )
            toggle_btn.setStyleSheet(
                f"""
                QPushButton {{
                    color: {Theme.TEXT_DISABLED};
                    background-color: transparent;
                    border: 2px solid {Theme.OUTLINE_VARIANT};
                    border-radius: 18px;
                    font-size: 20px;
                    font-weight: bold;
                    padding: 0;
                }}
                QPushButton:hover {{
                    border-color: {Theme.PRIMARY};
                    color: {Theme.PRIMARY};
                    background-color: {Theme.PRIMARY_CONTAINER};
                }}
                QPushButton:pressed {{
                    background-color: {Theme.SECONDARY_CONTAINER};
                }}
                """
            )
        toggle_btn.clicked.connect(lambda _checked, fid=folder_id: self._on_toggle(fid))
        row_layout.addWidget(toggle_btn)

        # Edit button (always present, shows folder alias for quick scanning)
        edit_text = f"Edit: {alias}" if alias else "Edit"
        edit_btn = QPushButton(edit_text)
        edit_btn.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
        edit_btn.setMinimumWidth(edit_button_min_width)
        edit_btn.setToolTip(
            f"Edit folder settings for '{alias}'" if alias else "Edit folder settings"
        )
        edit_btn.setAccessibleName(f"Edit folder {alias}" if alias else "Edit folder")
        edit_btn.setAccessibleDescription(
            f"Open settings for folder '{alias}'" if alias else "Open folder settings"
        )
        self._style_action_button(edit_btn)
        edit_btn.clicked.connect(lambda _checked, fid=folder_id: self._on_edit(fid))
        row_layout.addWidget(edit_btn, stretch=1)

        # Action buttons based on status
        if is_active:
            # Send button
            send_btn = QPushButton("Send")
            send_btn.setFixedWidth(64)
            send_btn.setSizePolicy(QSizePolicy.Policy.Fixed, QSizePolicy.Policy.Fixed)
            send_btn.setToolTip(f"Process only '{alias}'")
            send_btn.setAccessibleName(
                f"Send folder {alias}" if alias else "Send folder"
            )
            send_btn.setAccessibleDescription(
                f"Process only folder '{alias}'" if alias else "Process this folder"
            )
            self._style_action_button(send_btn, "primary")
            send_btn.clicked.connect(lambda _checked, fid=folder_id: self._on_send(fid))
            row_layout.addWidget(send_btn)
        else:
            # Delete button
            delete_btn = QPushButton("Delete")
            delete_btn.setFixedWidth(74)
            delete_btn.setSizePolicy(QSizePolicy.Policy.Fixed, QSizePolicy.Policy.Fixed)
            delete_btn.setToolTip(f"Remove '{alias}' from configured folders")
            delete_btn.setAccessibleName(
                f"Delete folder {alias}" if alias else "Delete folder"
            )
            delete_btn.setAccessibleDescription(
                f"Remove folder '{alias}' from configured folders"
                if alias
                else "Remove this folder from configured folders"
            )
            self._style_action_button(delete_btn, "danger")
            delete_btn.clicked.connect(
                lambda _checked, fid=folder_id, a=alias: self._on_delete(fid, a)
            )
            row_layout.addWidget(delete_btn)

        return row_widget

    def get_scroll_position(self) -> int:
        """Return the current vertical scroll position."""
        if self._scroll_area is not None:
            return self._scroll_area.verticalScrollBar().value()
        return 0

    def set_scroll_position(self, position: int) -> None:
        """Restore a previously saved vertical scroll position."""
        if self._scroll_area is not None:
            self._scroll_area.verticalScrollBar().setValue(position)

    def update_folder_row(self, folder_id: int) -> bool:
        """Replace a single folder row in-place after a state change.

        Re-reads the folder from the database, builds a new row widget, and
        swaps it into the scroll layout at the same position.

        Args:
            folder_id: The ID of the folder whose row should be refreshed.

        Returns:
            ``True`` if the row was found and replaced, ``False`` otherwise.
        """
        old_row = self._row_widgets.get(folder_id)
        if old_row is None or self._scroll_layout is None:
            return False

        folder = self._folders_table.find_one(id=folder_id)
        if folder is None:
            return False

        idx = self._scroll_layout.indexOf(old_row)
        if idx < 0:
            return False

        new_row = self._build_folder_row(folder, self._edit_button_min_width)

        self._scroll_layout.removeWidget(old_row)
        old_row.setParent(None)
        old_row.deleteLater()

        self._scroll_layout.insertWidget(idx, new_row)
        self._row_widgets[folder_id] = new_row
        return True

    # ------------------------------------------------------------------
    # Filtering
    # ------------------------------------------------------------------

    def apply_filter(self, filter_text: str) -> None:
        """Show/hide folder rows in-place based on a fuzzy filter.

        When *filter_text* is empty every row is shown.  Otherwise
        ``thefuzz`` fuzzy matching is used to determine which rows to keep
        visible.

        Args:
            filter_text: The search string (empty string shows all).
        """
        self._filter_value = filter_text

        if not filter_text:
            visible_ids = set(self._row_widgets.keys())
        else:
            if not self._folder_aliases:
                visible_ids = set()
            else:
                # Build a mapping of "id:alias" keys so each entry is unique,
                # then match by folder ID to avoid collisions between duplicate aliases.
                keyed = {str(fid): alias for fid, alias in self._folder_aliases.items()}
                fuzzy_matches = list(
                    thefuzz.process.extractWithoutOrder(
                        filter_text, keyed, score_cutoff=80
                    )
                )
                visible_ids = {int(m[2]) for m in fuzzy_matches}

        visible_count = 0
        for fid, row in self._row_widgets.items():
            is_visible = fid in visible_ids
            row.setVisible(is_visible)
            if is_visible:
                visible_count += 1

        if self._empty_label is not None:
            self._empty_label.setVisible(visible_count == 0 and bool(self._row_widgets))

        if self._total_count_callback is not None:
            self._total_count_callback(visible_count, len(self._row_widgets))

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    def _style_action_button(self, btn: QPushButton, variant: str = "default") -> None:
        """Apply modern styling to an action button.

        Sets a ``compact`` Qt property on the button and uses a QSS property
        selector so compact padding is applied without fragile string replacement.
        """
        btn.setCursor(Qt.CursorShape.PointingHandCursor)
        btn.setProperty("compact", True)
        base_stylesheet = Theme.get_button_stylesheet(variant)
        # Append a compact-padding override using the Qt property selector
        compact_override = f"""
            QPushButton[compact="true"] {{
                padding: {Theme.SPACING_SM} {Theme.SPACING_SM};
            }}
        """
        btn.setStyleSheet(base_stylesheet + compact_override)
        btn.style().unpolish(btn)
        btn.style().polish(btn)

    def _calculate_edit_button_min_width(
        self, folder_list: List[Dict[str, Any]]
    ) -> int:
        """Calculate a robust minimum width for edit buttons using font metrics."""
        edit_texts = [
            f"Edit: {entry.get('alias') or ''}".rstrip() for entry in folder_list
        ]
        if not edit_texts:
            edit_texts = ["Edit"]

        metrics = QFontMetrics(self.font())
        max_text_width = max(metrics.horizontalAdvance(text) for text in edit_texts)
        horizontal_padding = Theme.SPACING_XL_INT * 2
        border_allowance = 6
        return max_text_width + horizontal_padding + border_allowance
