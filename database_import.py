from tkinter import *
from tkinter.messagebox import askokcancel
from tkinter.ttk import *
import os
from tkinter.filedialog import askopenfilename

import dataset

from business_logic import db as bl_db

run_has_happened = False
new_database_path = ""


def import_interface(master_window, original_database_path, running_platform, backup_path, current_db_version):
    """UI wrapper to select a source DB file and import its active folders into the original DB.

    This function preserves the GUI interaction but delegates the actual merge work
    to business_logic.db.import_records, providing a progress callback to update the UI.
    """
    import_interface_window = Toplevel()
    import_interface_window.title("folders.db merging utility")
    import_interface_window.transient(master_window)
    import_interface_window.geometry("+%d+%d" % (master_window.winfo_rootx() + 50, master_window.winfo_rooty() + 50))
    import_interface_window.grab_set()
    import_interface_window.focus_set()

    def select_database():
        global new_database_path
        new_database_path = askopenfilename(parent=import_interface_window, initialdir=os.path.expanduser('~'))
        if os.path.exists(new_database_path):
            new_database_label.configure(text=new_database_path)
            process_database_files_button.configure(state=NORMAL)

    def database_migrate_job_wrapper():
        import_interface_window.unbind("<Escape>")
        global run_has_happened
        run_can_continue = False

        # Attempt to read version info from the incoming DB to warn the user when appropriate
        try:
            new_database_connection = dataset.connect('sqlite:///' + new_database_path)
            new_db_version = new_database_connection['version']
            new_db_version_dict = new_db_version.find_one(id=1)
            new_db_version_var = new_db_version_dict.get('version') if new_db_version_dict else None
        except Exception:
            new_db_version_dict = None
            new_db_version_var = None

        if new_db_version_var is None:
            # If we can't determine version, ask user to confirm
            run_can_continue = askokcancel(message="Could not determine database version. Continue with import?")
        else:
            try:
                if int(new_db_version_var) < 14:
                    run_can_continue = askokcancel(message="Database versions below 14 do not contain operating system"
                                                           " information.\n Folder paths are not portable between operating"
                                                           " systems.\nThere is no guarantee that the imported folders will "
                                                           "work, Continue?")
                elif int(new_db_version_var) >= 14:
                    if int(new_db_version_var) > int(current_db_version):
                        if askokcancel(message="The proposed database version is newer than the version supported by this "
                                               "program.\nContinue?"):
                            run_can_continue = askokcancel(
                                message="THIS WILL RESULT IN UNDEFINED BEHAVIOR, ARE YOU SURE YOU WANT TO CONTINUE?\n"
                                        "Backup is stored at: " + backup_path)
                    elif not new_db_version_dict.get('os') == running_platform:
                        run_can_continue = askokcancel(
                            message="The operating system specified in the configuration does"
                                    " not match the currently running operating system.\n"
                                    "There is no guarantee that the imported folders will work, "
                                    "Continue?")
                    else:
                        run_can_continue = True
            except Exception:
                run_can_continue = askokcancel(message="Version check failed, continue with import?")

        if run_can_continue is True:
            process_database_files_button.configure(state=DISABLED)
            select_database_button.configure(state=DISABLED)

            def progress_cb(count):
                try:
                    progress_bar.configure(maximum=1, value=count)
                except Exception:
                    pass

            # Delegate heavy lifting to business_logic.db
            bl_db.import_records(new_database_path, original_database_path=original_database_path, progress_callback=progress_cb)

            new_database_label.configure(text="Import Completed")
            select_database_button.configure(state=NORMAL)
            progress_bar.configure(maximum=1, value=0)
            run_has_happened = True

        import_interface_window.bind("<Escape>", close_database_import_window)

    new_database_file_frame = Frame(import_interface_window)
    go_button_frame = Frame(import_interface_window)
    progress_bar_frame = Frame(import_interface_window)

    select_database_button = Button(master=new_database_file_frame, text="Select New Database File",
                                    command=select_database)
    select_database_button.pack(anchor='w')

    new_database_label = Label(master=new_database_file_frame, text="No File Selected", relief=SUNKEN)
    new_database_label.pack(anchor='w')

    process_database_files_button = Button(master=go_button_frame, text="Import Active Folders",
                                           command=database_migrate_job_wrapper)

    process_database_files_button.configure(state=DISABLED)

    process_database_files_button.pack()

    progress_bar = Progressbar(master=progress_bar_frame)
    progress_bar.pack()

    def close_database_import_window(_=None):
        import_interface_window.destroy()

    new_database_file_frame.pack(anchor='w')
    go_button_frame.pack(side=LEFT, anchor='w')
    progress_bar_frame.pack(side=RIGHT, anchor='e')
    import_interface_window.minsize(300, import_interface_window.winfo_height())
    import_interface_window.resizable(width=TRUE, height=FALSE)
    import_interface_window.bind("<Escape>", close_database_import_window)
    master_window.wait_window(import_interface_window)
    return run_has_happened
