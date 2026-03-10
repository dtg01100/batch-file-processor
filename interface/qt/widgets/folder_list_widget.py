"""Folder list widget for displaying and managing folder configurations.

This module provides a Qt widget for displaying folders with inline status indicators
and action buttons for send, edit, enable/disable, and delete operations.

The widget creates a single scrollable list with each folder showing its active/inactive
status inline. Each folder row contains action buttons appropriate to its status.

Fuzzy matching via the ``thefuzz`` library is used to filter folders by alias
when a filter value is provided.
"""

from operator import itemgetter
from typing import Any, Callable, Dict, Iterator, List, Optional, Protocol

import thefuzz.process  # type: ignore
from PyQt6.QtCore import Qt
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
            **kwargs: Filter criteria, e.g. ``folder_is_active="True"``.

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

        self._build_widget()

    # ------------------------------------------------------------------
    # Widget construction
    # ------------------------------------------------------------------

    def _build_widget(self) -> None:
        """Build the complete folder list widget."""
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(Theme.SPACING_LG_INT)

        # Get all folders sorted by alias
        folders_dict_list: List[Dict[str, Any]] = list(
            self._folders_table.find(order_by="alias")
        )

        # Apply filter to the combined list
        filtered_folder_dict_list = self._apply_filter(folders_dict_list)

        if self._total_count_callback is not None:
            self._total_count_callback(
                len(filtered_folder_dict_list),
                self._folders_table.count(),
            )

        # Build single column with all folders
        folder_column = self._build_column(
            title="Folders",
            folder_list=filtered_folder_dict_list,
        )

        main_layout.addWidget(folder_column, stretch=1)

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
            QFrame[frame="separator"] {{
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
            f"""
            QScrollArea {{
                border: none;
                background-color: transparent;
            }}
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
            empty_label = QLabel(f"No {title}")
            empty_label.setStyleSheet(
                f"""
                color: {Theme.TEXT_TERTIARY};
                font-size: {Theme.FONT_SIZE_SM};
                font-style: italic;
            """
            )
            empty_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
            empty_label.setContentsMargins(
                Theme.SPACING_LG_INT,
                Theme.SPACING_XXL_INT,
                Theme.SPACING_LG_INT,
                Theme.SPACING_XXL_INT,
            )
            scroll_layout.addWidget(empty_label)

        max_alias_length = self._calculate_max_alias_length(folder_list)

        for folder in folder_list:
            row = self._build_folder_row(folder, max_alias_length)
            scroll_layout.addWidget(row)

        scroll_layout.addStretch(1)
        scroll_area.setWidget(scroll_content)
        container_layout.addWidget(scroll_area, stretch=1)

        return container

    def _build_folder_row(
        self,
        folder: Dict[str, Any],
        max_alias_length: int,
    ) -> QWidget:
        """Build a single folder row with status indicator and action buttons.

        Args:
            folder: A folder dictionary with ``id``, ``alias``, and ``folder_is_active`` keys.
            max_alias_length: The maximum alias character length, used to set
                a uniform edit-button width.

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
        is_active: bool = folder["folder_is_active"] == "True"

        # Status badge
        status_badge = QLabel("●")
        status_badge.setFixedWidth(24)
        status_badge.setAlignment(Qt.AlignmentFlag.AlignCenter)
        if is_active:
            status_badge.setStyleSheet(
                f"""
                color: {Theme.PRIMARY};
                font-size: 18px;
                font-weight: bold;
            """
            )
            status_badge.setToolTip("Active")
        else:
            status_badge.setStyleSheet(
                f"""
                color: {Theme.TEXT_DISABLED};
                font-size: 18px;
                font-weight: bold;
            """
            )
            status_badge.setToolTip("Inactive")

        row_layout.addWidget(status_badge)

        # Edit button (always present, expands to show folder alias)
        edit_text = "Edit"
        target_char_width = max_alias_length + 6
        edit_btn = QPushButton(edit_text)
        edit_btn.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
        edit_btn.setMinimumWidth(self._char_width_to_pixels(target_char_width))
        self._style_action_button(edit_btn)
        edit_btn.clicked.connect(lambda _checked, fid=folder_id: self._on_edit(fid))
        row_layout.addWidget(edit_btn, stretch=1)

        # Action buttons based on status
        if is_active:
            # Disable button
            toggle_btn = QPushButton("⏸")
            toggle_btn.setFixedWidth(40)
            toggle_btn.setSizePolicy(QSizePolicy.Policy.Fixed, QSizePolicy.Policy.Fixed)
            toggle_btn.setToolTip("Disable folder")
            self._style_action_button(toggle_btn)
            toggle_btn.clicked.connect(
                lambda _checked, fid=folder_id: self._on_toggle(fid)
            )
            row_layout.addWidget(toggle_btn)

            # Send button
            send_btn = QPushButton("Send")
            send_btn.setFixedWidth(64)
            send_btn.setSizePolicy(QSizePolicy.Policy.Fixed, QSizePolicy.Policy.Fixed)
            self._style_action_button(send_btn, "primary")
            send_btn.clicked.connect(lambda _checked, fid=folder_id: self._on_send(fid))
            row_layout.addWidget(send_btn)
        else:
            # Enable button
            toggle_btn = QPushButton("▶")
            toggle_btn.setFixedWidth(40)
            toggle_btn.setSizePolicy(QSizePolicy.Policy.Fixed, QSizePolicy.Policy.Fixed)
            toggle_btn.setToolTip("Enable folder")
            self._style_action_button(toggle_btn)
            toggle_btn.clicked.connect(
                lambda _checked, fid=folder_id: self._on_toggle(fid)
            )
            row_layout.addWidget(toggle_btn)

            # Delete button
            delete_btn = QPushButton("Delete")
            delete_btn.setFixedWidth(74)
            delete_btn.setSizePolicy(QSizePolicy.Policy.Fixed, QSizePolicy.Policy.Fixed)
            self._style_action_button(delete_btn, "danger")
            delete_btn.clicked.connect(
                lambda _checked, fid=folder_id, a=alias: self._on_delete(fid, a)
            )
            row_layout.addWidget(delete_btn)

        return row_widget

    # ------------------------------------------------------------------
    # Filtering
    # ------------------------------------------------------------------

    def _apply_filter(
        self,
        folders_dict_list: List[Dict[str, Any]],
    ) -> List[Dict[str, Any]]:
        """Apply fuzzy filtering to the folder list.

        When :attr:`_filter_value` is empty the list is returned unchanged.
        Otherwise, ``thefuzz.process.extractWithoutOrder`` is used with a
        ``score_cutoff`` of **80** to match folder aliases.

        Args:
            folders_dict_list: All folders ordered by alias.

        Returns:
            A list of filtered folders.
        """
        if self._filter_value == "":
            return list(folders_dict_list)

        folder_alias_list = [folder["alias"] for folder in folders_dict_list]

        fuzzy_filter = list(
            thefuzz.process.extractWithoutOrder(
                self._filter_value, folder_alias_list, score_cutoff=80
            )
        )
        fuzzy_filter.sort(key=itemgetter(1), reverse=True)
        fuzzy_filtered_alias = [fuzzy_alias for fuzzy_alias, _ in fuzzy_filter]

        # Match folders by alias in the order of fuzzy match scores
        filtered_folders: List[Dict[str, Any]] = []
        for alias in fuzzy_filtered_alias:
            matching = [f for f in folders_dict_list if f["alias"] == alias]
            if matching:
                filtered_folders.append(matching[0])

        return filtered_folders

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    def _style_action_button(self, btn: QPushButton, variant: str = "default") -> None:
        """Apply modern styling to an action button."""
        btn.setCursor(Qt.CursorShape.PointingHandCursor)
        if variant == "primary":
            btn.setObjectName("primary")
        elif variant == "danger":
            btn.setObjectName("danger")
        elif variant == "sidebar":
            btn.setObjectName("sidebar")

    @staticmethod
    def _calculate_max_alias_length(folder_list: List[Dict[str, Any]]) -> int:
        """Return the character length of the longest alias in *folder_list*.

        Args:
            folder_list: A list of folder dictionaries.

        Returns:
            The maximum alias length, or ``0`` if the list is empty or
            contains no aliases.
        """
        aliases = [
            entry["alias"] for entry in folder_list if entry.get("alias") is not None
        ]
        if aliases:
            return len(max(aliases, key=len))
        return 0

    @staticmethod
    def _char_width_to_pixels(char_count: int, avg_char_px: int = 8) -> int:
        """Convert a character count to an approximate pixel width.

        This is a rough heuristic used to give edit buttons a uniform
        minimum width comparable to the Tkinter ``width`` parameter.

        Args:
            char_count: The number of characters.
            avg_char_px: Approximate pixel width per character.

        Returns:
            The estimated pixel width.
        """
        return char_count * avg_char_px
