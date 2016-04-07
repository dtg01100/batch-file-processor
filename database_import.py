from Tkinter import *
from ttk import *
import os
import tkFileDialog
import mover


def import_interface(master_window, database_connection, original_database_path):
    import_interface_window = Toplevel()
    import_interface_window.title("folders.db merging utility")
    import_interface_window.transient(master_window)
    import_interface_window.geometry("+%d+%d" % (master_window.winfo_rootx() + 50, master_window.winfo_rooty() + 50))
    import_interface_window.grab_set()
    import_interface_window.focus_set()

    new_database_path = ""

    def select_database():
        global new_database_path
        global database_migrate_job
        new_database_path = tkFileDialog.askopenfilename()
        if os.path.exists(new_database_path):
            new_database_label.configure(text=new_database_path)
            process_database_files_button.configure(state=NORMAL)
            database_migrate_job = mover.DbMigrationThing(original_database_path, new_database_path)

    def database_migrate_job_wrapper():
        database_migrate_job.do_migrate(progress_bar, import_interface_window, database_connection)
        new_database_label.configure(text="Import Completed")
        progress_bar.configure(maximum=1, value=0)
        process_database_files_button.configure(state=DISABLED)

    new_database_file_frame = Frame(import_interface_window)
    go_button_frame = Frame(import_interface_window)
    progress_bar_frame = Frame(import_interface_window)

    Button(master=new_database_file_frame, text="Select New Database File",
           command=select_database).pack(anchor='w')

    new_database_label = Label(master=new_database_file_frame, text="No File Selected")
    new_database_label.pack(anchor='w')

    process_database_files_button = Button(master=go_button_frame, text="Import Active Folders",
                                           command=database_migrate_job_wrapper)

    process_database_files_button.configure(state=DISABLED)

    process_database_files_button.pack()

    progress_bar = Progressbar(master=progress_bar_frame)
    progress_bar.pack()

    new_database_file_frame.pack(anchor='w')
    go_button_frame.pack(side=LEFT, anchor='w')
    progress_bar_frame.pack(side=RIGHT, anchor='e')
    master_window.wait_window(import_interface_window)
