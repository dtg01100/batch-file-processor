from Tkinter import *
from ttk import *
import os
import tkFileDialog
import mover


def import_interface(master_window, original_database_path):
    global run_has_happened
    import_interface_window = Toplevel()
    import_interface_window.title("folders.db merging utility")
    import_interface_window.transient(master_window)
    import_interface_window.geometry("+%d+%d" % (master_window.winfo_rootx() + 50, master_window.winfo_rooty() + 50))
    import_interface_window.grab_set()
    import_interface_window.focus_set()
    run_has_happened = False

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
        import_interface_window.unbind("<Escape>", close_database_import_window)
        global run_has_happened
        process_database_files_button.configure(state=DISABLED)
        select_database_button.configure(state=DISABLED)
        database_migrate_job.do_migrate(progress_bar, import_interface_window, original_database_path)
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

    def close_database_import_window(event=None):
        import_interface_window.destroy()

    new_database_file_frame.pack(anchor='w')
    go_button_frame.pack(side=LEFT, anchor='w')
    progress_bar_frame.pack(side=RIGHT, anchor='e')
    import_interface_window.minsize(300, import_interface_window.winfo_height())
    import_interface_window.resizable(width=TRUE, height=FALSE)
    import_interface_window.bind("<Escape>", close_database_import_window)
    master_window.wait_window(import_interface_window)
    return run_has_happened
