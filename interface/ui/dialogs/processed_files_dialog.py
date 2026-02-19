"""ProcessedFilesDialog for viewing processed files reports.

This module provides the processed files dialog for the Batch File Sender application,
extracted from main_interface.py for better testability.
"""

import os
import tkinter
import tkinter.ttk
from typing import Any, Callable, Dict, List, Optional, Tuple

from operator import itemgetter

from tkinter.filedialog import askdirectory

import tk_extra_widgets


def export_processed_report(
    folder_id: int, 
    output_folder: str,
    database_obj: Any
) -> None:
    """Export a processed files report for a specific folder.

    Args:
        folder_id: ID of the folder to export report for
        output_folder: Directory to save the report
        database_obj: Database object for data access
    """

    def avoid_duplicate_export_file(file_name: str, file_extension: str) -> str:
        """Returns a file path that does not already exist.

        If the proposed file path exists, appends a number to the file name
        until an available file path is found.
        """
        print(f"Checking if {file_name + file_extension} exists")
        if not os.path.exists(file_name + file_extension):
            print(f"{file_name + file_extension} does not exist")
            return file_name + file_extension
        else:
            print(f"{file_name + file_extension} exists")
            i = 1
            while True:
                potential_file_path = (
                    file_name + " (" + str(i) + ")" + file_extension
                )
                print(f"Checking if {potential_file_path} exists")
                if not os.path.exists(potential_file_path):
                    print(f"{potential_file_path} does not exist")
                    return potential_file_path
                i += 1
                print(f"{potential_file_path} exists")

    folder_alias = database_obj.folders_table.find_one(id=folder_id)[
        "alias"
    ]

    export_file_path = avoid_duplicate_export_file(
        os.path.join(output_folder, folder_alias + " processed report"), ".csv"
    )
    print(f"Export file path will be: {export_file_path}")
    with open(export_file_path, "w", encoding="utf-8") as processed_log:
        processed_log.write(
            "File,Date,Copy Destination,FTP Destination,Email Destination\n"
        )
        for line in database_obj.processed_files.find(folder_id=folder_id):
            processed_log.write(
                f"{line['file_name']},"
                f"{line['sent_date_time'].strftime('%Y-%m-%d %H:%M:%S')},"
                f"{line['copy_destination']},"
                f"{line['ftp_destination']},"
                f"{line['email_destination']}"
                "\n"
            )
        print(
            f"Wrote {len(list(database_obj.processed_files.find(folder_id=folder_id)))} lines to {export_file_path}"
        )


def show_processed_files_dialog(
    root: tkinter.Tk,
    database_obj: Any,
) -> Optional[tkinter.Toplevel]:
    """Show the processed files popup dialog.

    Args:
        root: Parent window
        database_obj: Database object for data access

    Returns:
        The processed files popup window
    """
    # State variables (using mutable container for closure access)
    state = {
        "output_folder_is_confirmed": False,
        "processed_files_output_folder": "",
        "export_button": None,
    }

    def close_processed_files_popup(_=None):
        processed_files_popup_dialog.destroy()
        return

    def folder_button_pressed(name: int) -> None:
        """Handle folder button press."""
        for child in processed_files_popup_actions_frame.winfo_children():
            child.destroy()
        tkinter.ttk.Button(
            processed_files_popup_actions_frame,
            text="Choose output Folder",
            command=set_output_folder,
        ).pack(pady=10)
        export_button = tkinter.ttk.Button(
            processed_files_popup_actions_frame,
            text="Export Processed Report",
            command=lambda: export_processed_report(
                name, state["processed_files_output_folder"], database_obj
            ),
        )
        if state["output_folder_is_confirmed"] is False:
            export_button.configure(state=tkinter.DISABLED)
        else:
            export_button.configure(state=tkinter.NORMAL)
        export_button.pack(pady=10)
        state["export_button"] = export_button

    def set_output_folder() -> None:
        """Set the output folder for export."""
        set_output_prior_folder = (
            database_obj.oversight_and_defaults.find_one(id=1)
        )
        if set_output_prior_folder and os.path.exists(set_output_prior_folder.get("export_processed_folder_prior", "")):
            initial_directory = set_output_prior_folder[
                "export_processed_folder_prior"
            ]
        else:
            initial_directory = os.path.expanduser("~")
        output_folder_proposed = askdirectory(
            parent=processed_files_popup_actions_frame, initialdir=initial_directory
        )
        if output_folder_proposed == "":
            return
        else:
            output_folder = output_folder_proposed
        update_last_folder = dict(id=1, export_processed_folder_prior=output_folder)
        database_obj.oversight_and_defaults.update(
            update_last_folder, ["id"]
        )
        state["output_folder_is_confirmed"] = True
        state["processed_files_output_folder"] = output_folder
        if state["export_button"]:
            if state["output_folder_is_confirmed"] is False:
                state["export_button"].configure(state=tkinter.DISABLED)
            else:
                state["export_button"].configure(state=tkinter.NORMAL)

    # Initialize state from database
    prior_folder = database_obj.oversight_and_defaults.find_one(id=1)
    if prior_folder:
        state["processed_files_output_folder"] = prior_folder.get("export_processed_folder_prior", "")
    
    folder_button_variable = tkinter.IntVar()
    
    # Create popup window
    processed_files_popup_dialog = tkinter.Toplevel()
    processed_files_popup_dialog.title("Processed Files Report")
    processed_files_popup_dialog.transient(root)
    # center dialog on main window
    processed_files_popup_dialog.geometry(
        "+%d+%d" % (root.winfo_rootx() + 50, root.winfo_rooty() + 50)
    )
    processed_files_popup_dialog.grab_set()
    processed_files_popup_dialog.focus_set()
    processed_files_popup_dialog.resizable(
        width=tkinter.FALSE, height=tkinter.FALSE
    )
    
    # Create frames
    processed_files_popup_body_frame = tkinter.ttk.Frame(
        processed_files_popup_dialog
    )
    processed_files_popup_list_container = tkinter.ttk.Frame(
        processed_files_popup_body_frame
    )
    processed_files_popup_list_frame = tk_extra_widgets.VerticalScrolledFrame(
        processed_files_popup_list_container
    )
    processed_files_popup_close_frame = tkinter.ttk.Frame(
        processed_files_popup_dialog
    )
    processed_files_popup_actions_frame = tkinter.ttk.Frame(
        processed_files_popup_body_frame
    )
    processed_files_loading_label = tkinter.ttk.Label(
        master=processed_files_popup_dialog, text="Loading..."
    )
    processed_files_loading_label.pack()
    root.update()
    
    tkinter.ttk.Label(
        processed_files_popup_actions_frame, text="Select a Folder."
    ).pack(padx=10)
    
    if database_obj.processed_files.count() == 0:
        no_processed_label = tkinter.ttk.Label(
            processed_files_popup_list_frame, text="No Folders With Processed Files"
        )
        no_processed_label.pack(fill=tkinter.BOTH, expand=1, padx=10)
    
    processed_files_distinct_list: List[int] = []
    for row in database_obj.processed_files.distinct("folder_id"):
        processed_files_distinct_list.append(row["folder_id"])
    
    folder_entry_tuple_list: List[Tuple[int, str]] = []
    for entry in processed_files_distinct_list:
        folder_dict = database_obj.folders_table.find_one(id=str(entry))
        if folder_dict is None:
            continue
        folder_alias = folder_dict["alias"]
        folder_entry_tuple_list.append((entry, folder_alias))
    sorted_folder_list = sorted(folder_entry_tuple_list, key=itemgetter(1))

    for folders_name, folder_alias in sorted_folder_list:
        folder_row = database_obj.processed_files.find_one(
            folder_id=str(folders_name)
        )
        if folder_row:
            tkinter.Radiobutton(
                processed_files_popup_list_frame.interior,
                text=folder_alias.center(15),
                variable=folder_button_variable,
                value=folder_alias,
                indicatoron=tkinter.FALSE,
                command=lambda name=folder_row["folder_id"]: folder_button_pressed(
                    name
                ),
            ).pack(anchor="w", fill="x")
    
    close_button = tkinter.ttk.Button(
        processed_files_popup_close_frame,
        text="Close",
        command=close_processed_files_popup,
    )
    close_button.pack(pady=5)
    processed_files_popup_dialog.bind("<Escape>", close_processed_files_popup)
    processed_files_loading_label.destroy()
    processed_files_popup_list_container.pack(side=tkinter.LEFT)
    processed_files_popup_list_frame.pack()
    processed_files_popup_actions_frame.pack(
        side=tkinter.RIGHT, anchor=tkinter.N, padx=5
    )
    processed_files_popup_body_frame.pack()
    tkinter.ttk.Separator(
        master=processed_files_popup_dialog, orient=tkinter.HORIZONTAL
    ).pack(fill="x")
    processed_files_popup_close_frame.pack()

    return processed_files_popup_dialog
