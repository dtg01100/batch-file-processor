"""Folder list widget for displaying and managing folder configurations.

This module provides a widget for displaying active and inactive folders
with action buttons for send, edit, disable, and delete operations.
"""

import tkinter
import tkinter.ttk
from operator import itemgetter
from typing import Any, Callable, Dict, Iterator, List, Optional, Protocol

import thefuzz.process  # type: ignore
import tk_extra_widgets


class FolderTableProtocol(Protocol):
    """Protocol for folder table operations."""
    
    def find(self, **kwargs) -> Iterator[Dict[str, Any]]: ...
    def count(self, **kwargs) -> int: ...
    def find_one(self, **kwargs) -> Optional[Dict[str, Any]]: ...


class FolderListWidget:
    """A widget displaying active and inactive folder lists with actions.
    
    This widget creates scrollable lists of folders separated into active
    and inactive sections. Each folder has action buttons for common operations.
    
    The widget supports fuzzy filtering of folders by alias name.
    
    Attributes:
        frame: The main containing frame for the widget
    
    Example:
        >>> def on_send(folder_id: int): ...
        >>> def on_edit(folder_id: int): ...
        >>> def on_disable(folder_id: int): ...
        >>> def on_delete(folder_id: int, alias: str): ...
        >>> 
        >>> widget = FolderListWidget(
        ...     parent=root_frame,
        ...     folders_table=database.folders_table,
        ...     on_send=on_send,
        ...     on_edit=on_edit,
        ...     on_disable=on_disable,
        ...     on_delete=on_delete,
        ...     filter_value=""
        ... )
        >>> widget.pack()
    """
    
    def __init__(
        self,
        parent: tkinter.Tk,
        folders_table: FolderTableProtocol,
        on_send: Callable[[int], None],
        on_edit: Callable[[int], None],
        on_disable: Callable[[int], None],
        on_delete: Callable[[int, str], None],
        filter_value: str = "",
        total_count_callback: Optional[Callable[[int, int], None]] = None,
    ):
        """Initialize the folder list widget.
        
        Args:
            parent: The parent window/frame
            folders_table: The database table containing folder configurations
            on_send: Callback for send button (receives folder ID)
            on_edit: Callback for edit button (receives folder ID)
            on_disable: Callback for disable button (receives folder ID)
            on_delete: Callback for delete button (receives folder ID and alias)
            filter_value: Current filter value for fuzzy matching
            total_count_callback: Optional callback for filtered/total counts
        """
        self._parent = parent
        self._folders_table = folders_table
        self._on_send = on_send
        self._on_edit = on_edit
        self._on_disable = on_disable
        self._on_delete = on_delete
        self._filter_value = filter_value
        self._total_count_callback = total_count_callback
        
        # Create main frame
        self._frame = tkinter.ttk.Frame(parent)
        
        # Build the widget
        self._build_widget()
    
    @property
    def frame(self) -> tkinter.ttk.Frame:
        """Get the main containing frame."""
        return self._frame
    
    def pack(self, **kwargs) -> None:
        """Pack the widget frame."""
        self._frame.pack(**kwargs)
    
    def destroy(self) -> None:
        """Destroy the widget."""
        self._frame.destroy()
    
    def _build_widget(self) -> None:
        """Build the folder list widget."""
        # Create scrollable lists frame
        scrollable_lists_frame = tkinter.ttk.Frame(self._frame)
        
        # Create containers for active and inactive lists
        active_users_list_container = tkinter.ttk.Frame(scrollable_lists_frame)
        inactive_users_list_container = tkinter.ttk.Frame(scrollable_lists_frame)
        
        # Create scrolled frames for each list
        active_users_list_frame = tk_extra_widgets.VerticalScrolledFrame(
            active_users_list_container
        )
        inactive_users_list_frame = tk_extra_widgets.VerticalScrolledFrame(
            inactive_users_list_container
        )
        
        # Create labels
        active_users_list_label = tkinter.ttk.Label(
            active_users_list_container, text="Active Folders"
        )
        inactive_users_list_label = tkinter.ttk.Label(
            inactive_users_list_container, text="Inactive Folders"
        )
        
        # Get folder data
        active_folder_dict_list = list(self._folders_table.find(
            folder_is_active="True"
        ))
        inactive_folder_dict_list = list(self._folders_table.find(
            folder_is_active="False"
        ))
        folders_dict_list = list(self._folders_table.find(order_by="alias"))
        
        # Apply filter if set
        filtered_folder_dict_list, filtered_active_folder_dict_list, filtered_inactive_folder_dict_list = \
            self._apply_filter(
                folders_dict_list,
                active_folder_dict_list,
                inactive_folder_dict_list
            )
        
        # Notify about counts if callback provided
        if self._total_count_callback:
            self._total_count_callback(
                len(filtered_folder_dict_list),
                self._folders_table.count()
            )
        
        # Create empty list labels if needed
        self._create_empty_labels(
            filtered_folder_dict_list,
            filtered_active_folder_dict_list,
            filtered_inactive_folder_dict_list,
            active_users_list_frame,
            inactive_users_list_frame
        )
        
        # Calculate button widths
        active_folder_edit_length = self._calculate_max_alias_length(
            filtered_active_folder_dict_list
        )
        inactive_folder_edit_length = self._calculate_max_alias_length(
            filtered_inactive_folder_dict_list
        )
        
        # Create folder buttons
        self._create_folder_buttons(
            filtered_folder_dict_list,
            active_users_list_frame,
            inactive_users_list_frame,
            active_folder_edit_length,
            inactive_folder_edit_length
        )
        
        # Pack all widgets
        self._pack_widgets(
            active_users_list_label,
            inactive_users_list_label,
            active_users_list_container,
            inactive_users_list_container,
            active_users_list_frame,
            inactive_users_list_frame,
            scrollable_lists_frame
        )
    
    def _apply_filter(
        self,
        folders_dict_list: List[Dict[str, Any]],
        active_folder_dict_list: List[Dict[str, Any]],
        inactive_folder_dict_list: List[Dict[str, Any]]
    ) -> tuple:
        """Apply fuzzy filter to folder lists.
        
        Args:
            folders_dict_list: All folders
            active_folder_dict_list: Active folders
            inactive_folder_dict_list: Inactive folders
            
        Returns:
            Tuple of (filtered_all, filtered_active, filtered_inactive)
        """
        if self._filter_value == "":
            return (
                list(folders_dict_list),
                list(active_folder_dict_list),
                list(inactive_folder_dict_list)
            )
        
        # Build alias list for fuzzy matching
        folder_alias_list = [folder["alias"] for folder in folders_dict_list]
        
        # Perform fuzzy matching
        fuzzy_filter = list(
            thefuzz.process.extractWithoutOrder(
                self._filter_value, folder_alias_list, score_cutoff=80
            )
        )
        fuzzy_filter.sort(key=itemgetter(1), reverse=True)
        fuzzy_filtered_alias = [fuzzy_alias for fuzzy_alias, _ in fuzzy_filter]
        
        # Filter the lists
        def copyf(dictlist, key, valuelist):
            return [dictio for dictio in dictlist if dictio[key] in valuelist]
        
        pre_filtered_folder_dict_list = []
        pre_filtered_active_folder_dict_list = []
        pre_filtered_inactive_folder_dict_list = []
        
        for entry in fuzzy_filtered_alias:
            pre_filtered_folder_dict_list.append(
                copyf(folders_dict_list, "alias", entry)
            )
            pre_filtered_active_folder_dict_list.append(
                copyf(active_folder_dict_list, "alias", entry)
            )
            pre_filtered_inactive_folder_dict_list.append(
                copyf(inactive_folder_dict_list, "alias", entry)
            )
        
        filtered_folder_dict_list = [
            i[0] for i in pre_filtered_folder_dict_list if i
        ]
        filtered_active_folder_dict_list = [
            i[0] for i in pre_filtered_active_folder_dict_list if i
        ]
        filtered_inactive_folder_dict_list = [
            i[0] for i in pre_filtered_inactive_folder_dict_list if i
        ]
        
        return (
            filtered_folder_dict_list,
            filtered_active_folder_dict_list,
            filtered_inactive_folder_dict_list
        )
    
    def _create_empty_labels(
        self,
        filtered_folder_dict_list: List[Dict[str, Any]],
        filtered_active_folder_dict_list: List[Dict[str, Any]],
        filtered_inactive_folder_dict_list: List[Dict[str, Any]],
        active_frame: tk_extra_widgets.VerticalScrolledFrame,
        inactive_frame: tk_extra_widgets.VerticalScrolledFrame
    ) -> None:
        """Create labels for empty folder lists.
        
        Args:
            filtered_folder_dict_list: All filtered folders
            filtered_active_folder_dict_list: Filtered active folders
            filtered_inactive_folder_dict_list: Filtered inactive folders
            active_frame: Frame for active folders
            inactive_frame: Frame for inactive folders
        """
        if len(filtered_folder_dict_list) == 0:
            no_active_label = tkinter.ttk.Label(
                active_frame, text="No Active Folders"
            )
            no_active_label.pack(fill=tkinter.BOTH, expand=1, padx=10)
            no_inactive_label = tkinter.ttk.Label(
                inactive_frame, text="No Inactive Folders"
            )
            no_inactive_label.pack(fill=tkinter.BOTH, expand=1, padx=10)
        else:
            if len(filtered_active_folder_dict_list) == 0:
                no_active_label = tkinter.ttk.Label(
                    active_frame, text="No Active Folders"
                )
                no_active_label.pack(fill=tkinter.BOTH, expand=1, padx=10)
            if len(filtered_inactive_folder_dict_list) == 0:
                no_inactive_label = tkinter.ttk.Label(
                    inactive_frame, text="No Inactive Folders"
                )
                no_inactive_label.pack(fill=tkinter.BOTH, expand=1, padx=10)
    
    def _calculate_max_alias_length(
        self,
        folder_list: List[Dict[str, Any]]
    ) -> int:
        """Calculate the maximum alias length in a folder list.
        
        Args:
            folder_list: List of folder dictionaries
            
        Returns:
            Maximum alias length, or 0 if list is empty
        """
        alias_list = []
        for entry in folder_list:
            alias = entry.get("alias")
            if alias is not None:
                alias_list.append(alias)
        
        if alias_list:
            return len(max(alias_list, key=len))
        return 0
    
    def _create_folder_buttons(
        self,
        filtered_folder_dict_list: List[Dict[str, Any]],
        active_frame: tk_extra_widgets.VerticalScrolledFrame,
        inactive_frame: tk_extra_widgets.VerticalScrolledFrame,
        active_width: int,
        inactive_width: int
    ) -> None:
        """Create action buttons for each folder.
        
        Args:
            filtered_folder_dict_list: Filtered folder list
            active_frame: Frame for active folders
            inactive_frame: Frame for inactive folders
            active_width: Button width for active folders
            inactive_width: Button width for inactive folders
        """
        for folders_name in filtered_folder_dict_list:
            if str(folders_name.get("folder_is_active")) != "False":
                # Active folder
                active_folder_button_frame = tkinter.ttk.Frame(
                    active_frame.interior
                )
                tkinter.ttk.Button(
                    active_folder_button_frame,
                    text="Send",
                    command=lambda name=folders_name["id"]: self._on_send(name),
                ).grid(column=2, row=0, padx=(0, 10))
                tkinter.ttk.Button(
                    active_folder_button_frame,
                    text="<-",
                    command=lambda name=folders_name["id"]: self._on_disable(name),
                ).grid(column=0, row=0)
                tkinter.ttk.Button(
                    active_folder_button_frame,
                    text="Edit: " + folders_name["alias"] + "...",
                    command=lambda name=folders_name["id"]: self._on_edit(name),
                    width=active_width + 6,
                ).grid(column=1, row=0, sticky=tkinter.E + tkinter.W)
                active_folder_button_frame.pack(anchor="e", pady=1)
            else:
                # Inactive folder
                inactive_folder_button_frame = tkinter.ttk.Frame(
                    inactive_frame.interior
                )
                tkinter.ttk.Button(
                    inactive_folder_button_frame,
                    text="Delete",
                    command=lambda name=folders_name["id"], alias=folders_name["alias"]: (
                        self._on_delete(name, alias)
                    ),
                ).grid(column=1, row=0, sticky=tkinter.E, padx=(0, 10))
                tkinter.ttk.Button(
                    inactive_folder_button_frame,
                    text="Edit: " + folders_name["alias"] + "...",
                    command=lambda name=folders_name["id"]: self._on_edit(name),
                    width=inactive_width + 6,
                ).grid(column=0, row=0, sticky=tkinter.E + tkinter.W, padx=(10, 0))
                inactive_folder_button_frame.pack(anchor="e", pady=1)
    
    def _pack_widgets(
        self,
        active_label: tkinter.ttk.Label,
        inactive_label: tkinter.ttk.Label,
        active_container: tkinter.ttk.Frame,
        inactive_container: tkinter.ttk.Frame,
        active_frame: tk_extra_widgets.VerticalScrolledFrame,
        inactive_frame: tk_extra_widgets.VerticalScrolledFrame,
        scrollable_frame: tkinter.ttk.Frame
    ) -> None:
        """Pack all widgets in the correct order.
        
        Args:
            active_label: Label for active folders section
            inactive_label: Label for inactive folders section
            active_container: Container for active folders
            inactive_container: Container for inactive folders
            active_frame: Scrolled frame for active folders
            inactive_frame: Scrolled frame for inactive folders
            scrollable_frame: Main scrollable frame container
        """
        # Pack labels and separators
        active_label.pack(pady=5)
        tkinter.ttk.Separator(
            active_container, orient=tkinter.HORIZONTAL
        ).pack(fill=tkinter.X)
        inactive_label.pack(pady=5)
        tkinter.ttk.Separator(
            inactive_container, orient=tkinter.HORIZONTAL
        ).pack(fill=tkinter.X)
        
        # Pack scrolled frames
        active_frame.pack(
            fill=tkinter.BOTH, expand=tkinter.TRUE, anchor=tkinter.E, padx=3, pady=3
        )
        inactive_frame.pack(
            fill=tkinter.BOTH, expand=tkinter.TRUE, anchor=tkinter.E, padx=3, pady=3
        )
        
        # Pack containers
        active_container.pack(
            side=tkinter.RIGHT, expand=tkinter.TRUE, fill=tkinter.Y
        )
        inactive_container.pack(
            side=tkinter.LEFT, expand=tkinter.TRUE, fill=tkinter.Y
        )
        
        # Pack main scrollable frame
        scrollable_frame.pack(
            side=tkinter.BOTTOM, expand=tkinter.TRUE, fill=tkinter.Y
        )
        
        # Add separator at top
        tkinter.ttk.Separator(self._frame, orient=tkinter.HORIZONTAL).pack(
            side=tkinter.BOTTOM, fill=tkinter.X
        )
