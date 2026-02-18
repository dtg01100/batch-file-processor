"""Folder list widget for displaying and managing folder configurations.

This module provides a Qt widget for displaying active and inactive folders
with action buttons for send, edit, disable, and delete operations.

The widget creates two side-by-side scrollable columns: inactive folders on
the left and active folders on the right. Each folder row contains action
buttons with uniform width based on the longest alias in its column.

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
    """A widget displaying active and inactive folder lists with actions.

    This widget creates scrollable lists of folders separated into active
    and inactive sections arranged side-by-side.  Each folder has action
    buttons for common operations such as send, edit, disable, and delete.

    The widget supports fuzzy filtering of folders by alias name using the
    ``thefuzz`` library with a score cutoff of 80.

    Args:
        parent: The parent widget.
        folders_table: The database table containing folder configurations.
        on_send: Callback for the *Send* button (receives folder ID).
        on_edit: Callback for the *Edit* button (receives folder ID).
        on_disable: Callback for the *Disable* (``<-``) button (receives folder ID).
        on_delete: Callback for the *Delete* button (receives folder ID and alias).
        filter_value: Current filter value for fuzzy matching.  An empty
            string disables filtering.
        total_count_callback: Optional callback invoked with
            ``(filtered_count, total_count)`` after folders are loaded.

    Example::

        >>> def on_send(folder_id: int) -> None: ...
        >>> def on_edit(folder_id: int) -> None: ...
        >>> def on_disable(folder_id: int) -> None: ...
        >>> def on_delete(folder_id: int, alias: str) -> None: ...
        >>>
        >>> widget = FolderListWidget(
        ...     parent=window,
        ...     folders_table=database.folders_table,
        ...     on_send=on_send,
        ...     on_edit=on_edit,
        ...     on_disable=on_disable,
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
        on_disable: Callable[[int], None],
        on_delete: Callable[[int, str], None],
        filter_value: str = "",
        total_count_callback: Optional[Callable[[int, int], None]] = None,
    ) -> None:
        super().__init__(parent)
        self._folders_table = folders_table
        self._on_send = on_send
        self._on_edit = on_edit
        self._on_disable = on_disable
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

        separator_top = QFrame()
        separator_top.setFrameShape(QFrame.Shape.HLine)
        separator_top.setFrameShadow(QFrame.Shadow.Sunken)
        main_layout.addWidget(separator_top)

        columns_layout = QHBoxLayout()
        columns_layout.setContentsMargins(0, 0, 0, 0)

        active_folder_dict_list: List[Dict[str, Any]] = list(
            self._folders_table.find(folder_is_active="True")
        )
        inactive_folder_dict_list: List[Dict[str, Any]] = list(
            self._folders_table.find(folder_is_active="False")
        )
        folders_dict_list: List[Dict[str, Any]] = list(
            self._folders_table.find(order_by="alias")
        )

        (
            filtered_folder_dict_list,
            filtered_active_folder_dict_list,
            filtered_inactive_folder_dict_list,
        ) = self._apply_filter(
            folders_dict_list,
            active_folder_dict_list,
            inactive_folder_dict_list,
        )

        if self._total_count_callback is not None:
            self._total_count_callback(
                len(filtered_folder_dict_list),
                self._folders_table.count(),
            )

        inactive_column = self._build_column(
            title="Inactive Folders",
            folder_list=filtered_inactive_folder_dict_list,
            all_filtered=filtered_folder_dict_list,
            is_active=False,
        )
        active_column = self._build_column(
            title="Active Folders",
            folder_list=filtered_active_folder_dict_list,
            all_filtered=filtered_folder_dict_list,
            is_active=True,
        )

        columns_layout.addWidget(inactive_column, stretch=1)
        columns_layout.addWidget(active_column, stretch=1)

        main_layout.addLayout(columns_layout, stretch=1)

    def _build_column(
        self,
        title: str,
        folder_list: List[Dict[str, Any]],
        all_filtered: List[Dict[str, Any]],
        is_active: bool,
    ) -> QWidget:
        """Build a single scrollable column for active or inactive folders.

        Args:
            title: The column header text (e.g. ``"Active Folders"``).
            folder_list: The filtered folders belonging to this column.
            all_filtered: All filtered folders (used to determine whether
                "no folders" labels should be shown).
            is_active: ``True`` when building the active column.

        Returns:
            A :class:`QWidget` containing the titled, scrollable column.
        """
        container = QWidget()
        container_layout = QVBoxLayout(container)
        container_layout.setContentsMargins(0, 0, 0, 0)

        header = QLabel(title)
        header.setAlignment(Qt.AlignmentFlag.AlignCenter)
        container_layout.addWidget(header)

        separator = QFrame()
        separator.setFrameShape(QFrame.Shape.HLine)
        separator.setFrameShadow(QFrame.Shadow.Sunken)
        container_layout.addWidget(separator)

        scroll_area = QScrollArea()
        scroll_area.setWidgetResizable(True)
        scroll_area.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
        scroll_area.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)

        scroll_content = QWidget()
        scroll_layout = QVBoxLayout(scroll_content)
        scroll_layout.setContentsMargins(3, 3, 3, 3)
        scroll_layout.setSpacing(2)

        if not all_filtered or not folder_list:
            empty_label = QLabel(f"No {title}")
            empty_label.setContentsMargins(10, 0, 10, 0)
            scroll_layout.addWidget(empty_label)

        max_alias_length = self._calculate_max_alias_length(folder_list)

        for folder in folder_list:
            row = self._build_folder_row(
                folder, is_active, max_alias_length
            )
            scroll_layout.addWidget(row)

        scroll_layout.addStretch(1)
        scroll_area.setWidget(scroll_content)
        container_layout.addWidget(scroll_area, stretch=1)

        return container

    def _build_folder_row(
        self,
        folder: Dict[str, Any],
        is_active: bool,
        max_alias_length: int,
    ) -> QWidget:
        """Build a single folder row with its action buttons.

        Args:
            folder: A folder dictionary with ``id`` and ``alias`` keys.
            is_active: ``True`` if this is an active-folder row.
            max_alias_length: The maximum alias character length in the
                column, used to set a uniform edit-button width.

        Returns:
            A :class:`QWidget` representing the folder row.
        """
        row_widget = QWidget()
        row_layout = QHBoxLayout(row_widget)
        row_layout.setContentsMargins(0, 1, 0, 1)
        row_layout.setSpacing(2)

        folder_id: int = folder["id"]
        alias: str = folder["alias"]

        edit_text = f"Edit: {alias}..."
        target_char_width = max_alias_length + 6

        if is_active:
            disable_btn = QPushButton("<-")
            disable_btn.setSizePolicy(QSizePolicy.Policy.Fixed, QSizePolicy.Policy.Fixed)
            disable_btn.clicked.connect(lambda _checked, fid=folder_id: self._on_disable(fid))

            edit_btn = QPushButton(edit_text)
            edit_btn.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
            edit_btn.setMinimumWidth(self._char_width_to_pixels(target_char_width))
            edit_btn.clicked.connect(lambda _checked, fid=folder_id: self._on_edit(fid))

            send_btn = QPushButton("Send")
            send_btn.setSizePolicy(QSizePolicy.Policy.Fixed, QSizePolicy.Policy.Fixed)
            send_btn.clicked.connect(lambda _checked, fid=folder_id: self._on_send(fid))

            row_layout.addWidget(disable_btn)
            row_layout.addWidget(edit_btn, stretch=1)
            row_layout.addWidget(send_btn)
        else:
            edit_btn = QPushButton(edit_text)
            edit_btn.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
            edit_btn.setMinimumWidth(self._char_width_to_pixels(target_char_width))
            edit_btn.clicked.connect(lambda _checked, fid=folder_id: self._on_edit(fid))

            delete_btn = QPushButton("Delete")
            delete_btn.setSizePolicy(QSizePolicy.Policy.Fixed, QSizePolicy.Policy.Fixed)
            delete_btn.clicked.connect(
                lambda _checked, fid=folder_id, a=alias: self._on_delete(fid, a)
            )

            row_layout.addWidget(edit_btn, stretch=1)
            row_layout.addWidget(delete_btn)

        return row_widget

    # ------------------------------------------------------------------
    # Filtering
    # ------------------------------------------------------------------

    def _apply_filter(
        self,
        folders_dict_list: List[Dict[str, Any]],
        active_folder_dict_list: List[Dict[str, Any]],
        inactive_folder_dict_list: List[Dict[str, Any]],
    ) -> tuple:
        """Apply fuzzy filtering to the folder lists.

        When :attr:`_filter_value` is empty the lists are returned unchanged.
        Otherwise, ``thefuzz.process.extractWithoutOrder`` is used with a
        ``score_cutoff`` of **80** to match folder aliases.

        Args:
            folders_dict_list: All folders ordered by alias.
            active_folder_dict_list: Active folders.
            inactive_folder_dict_list: Inactive folders.

        Returns:
            A tuple of ``(filtered_all, filtered_active, filtered_inactive)``
            lists.
        """
        if self._filter_value == "":
            return (
                list(folders_dict_list),
                list(active_folder_dict_list),
                list(inactive_folder_dict_list),
            )

        folder_alias_list = [folder["alias"] for folder in folders_dict_list]

        fuzzy_filter = list(
            thefuzz.process.extractWithoutOrder(
                self._filter_value, folder_alias_list, score_cutoff=80
            )
        )
        fuzzy_filter.sort(key=itemgetter(1), reverse=True)
        fuzzy_filtered_alias = [fuzzy_alias for fuzzy_alias, _ in fuzzy_filter]

        def _copy_matching(
            dictlist: List[Dict[str, Any]], key: str, value: Any
        ) -> List[Dict[str, Any]]:
            return [d for d in dictlist if d[key] == value]

        pre_filtered_all: List[List[Dict[str, Any]]] = []
        pre_filtered_active: List[List[Dict[str, Any]]] = []
        pre_filtered_inactive: List[List[Dict[str, Any]]] = []

        for entry in fuzzy_filtered_alias:
            pre_filtered_all.append(
                _copy_matching(folders_dict_list, "alias", entry)
            )
            pre_filtered_active.append(
                _copy_matching(active_folder_dict_list, "alias", entry)
            )
            pre_filtered_inactive.append(
                _copy_matching(inactive_folder_dict_list, "alias", entry)
            )

        filtered_all = [i[0] for i in pre_filtered_all if i]
        filtered_active = [i[0] for i in pre_filtered_active if i]
        filtered_inactive = [i[0] for i in pre_filtered_inactive if i]

        return filtered_all, filtered_active, filtered_inactive

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

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
            entry["alias"]
            for entry in folder_list
            if entry.get("alias") is not None
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
