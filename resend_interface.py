import os
import tkinter
from tkinter import *
from tkinter.messagebox import showerror
from tkinter.ttk import *

import tk_extra_widgets
from interface.services.resend_service import ResendService


def do(database_connection, master_window):
    try:
        service = ResendService(database_connection)
        if not service.has_processed_files():
            showerror(message="Nothing To Configure")
            return
    except Exception as e:
        showerror(message=f"Database error: {e}")
        return
    folder_button_variable = IntVar()
    files_count_variable = StringVar()
    files_count_variable.set(str(10))
    file_list = []
    file_name_length = 0
    folder_id = None
    resend_interface = Toplevel()
    resend_interface.title("Enable Resend")
    resend_interface.transient(master_window)
    resend_interface.geometry("+%d+%d" % (master_window.winfo_rootx() + 50, master_window.winfo_rooty() + 50))
    resend_interface.grab_set()
    resend_interface.focus_set()
    resend_interface.resizable(width=FALSE, height=FALSE)
    resend_interface_files_and_folders_frame = Frame(resend_interface)
    resend_interface_file_count_frame = Frame(resend_interface)
    resend_interface_folders_frame = Frame(resend_interface_files_and_folders_frame)
    resend_interface_files_frame = Frame(resend_interface_files_and_folders_frame)
    resend_interface_close_frame = Frame(resend_interface)

    def set_resend_flag(identifier, resend_flag):
        try:
            service.set_resend_flag(identifier, resend_flag)
        except Exception as e:
            showerror(message=f"Database error: {e}")

    def make_file_checkbutton_list(_=None):
        nonlocal file_list
        nonlocal file_name_length
        for child in resend_interface_scrollable_files_frame.interior.winfo_children():
            try:
                if child.winfo_exists():
                    child.destroy()
            except tkinter.TclError:
                pass
        if folder_id is None:
            return
        file_list = service.get_files_for_folder(
            folder_id, limit=int(resend_interface_files_list_count_spinbox.get())
        )
        file_name_list = [f['file_name'] for f in file_list]
        if file_name_list:
            file_name_length = len(os.path.basename(max(file_name_list, key=len)))
        else:
            file_name_length = 0
        for file_info in file_list:
            CheckButtons(resend_interface_scrollable_files_frame.interior,
                         file_info['file_name'], file_info['resend_flag'],
                         file_info['id'], file_info['sent_date_time'],
                         file_name_length)

    def folder_button_pressed(button):
        def round_to_next5(n):
            return n + (5 - n) % 5
        nonlocal folder_id
        nonlocal file_list
        folder_id = button.get()
        number_of_files = service.count_files_for_folder(folder_id)
        file_list = service.get_files_for_folder(
            folder_id, limit=int(resend_interface_files_list_count_spinbox.get())
        )
        resend_interface_files_list_count_spinbox.configure(state='normal')
        resend_interface_files_list_count_spinbox.configure(
            to=(round_to_next5(number_of_files) if number_of_files > 10 else 10))
        if int(resend_interface_files_list_count_spinbox.get()) > number_of_files:
            resend_interface_files_list_count_spinbox.delete(0, "end")
            resend_interface_files_list_count_spinbox.insert(0, str(
                round_to_next5(number_of_files) if number_of_files > 10 else 10))
        resend_interface_files_list_count_spinbox.configure(state='readonly')
        make_file_checkbutton_list()

    class CheckButtons:
        def __init__(self, master, file_name, resend_flag, identifier, sent_date_time, checkbutton_file_name_length):
            self.identifier = identifier
            self.resend_flag = resend_flag
            self.file_name = file_name
            self.var = BooleanVar()
            self.var.set(self.resend_flag)
            self.file_name_length = checkbutton_file_name_length
            c = Checkbutton(master=master,
                            text=os.path.basename(file_name).ljust(self.file_name_length) + " (" +
                            str(sent_date_time)[:-16].replace("-", "/") + ")",
                            variable=self.var,
                            onvalue=True,
                            offvalue=False,
                            command=self.cb)
            c.pack(anchor="e", fill=X, padx=5)
            Separator(master=master, orient=HORIZONTAL).pack(fill='x')

        def cb(self):
            set_resend_flag(self.identifier, self.var.get())

    loading_label = Label(master=resend_interface, text="Loading...")
    loading_label.pack()
    master_window.update()

    sorted_folder_list = service.get_folder_list()

    resend_interface_scrollable_folders_frame = tk_extra_widgets.VerticalScrolledFrame(resend_interface_folders_frame)
    resend_interface_scrollable_files_frame = tk_extra_widgets.VerticalScrolledFrame(resend_interface_files_frame)
    Label(master=resend_interface_scrollable_files_frame.interior, text="Select a Folder.").pack(padx=10)

    for folder, alias in sorted_folder_list:
        tkinter.Radiobutton(resend_interface_scrollable_folders_frame.interior, text=alias.center(15),
                            variable=folder_button_variable,
                            value=folder, indicatoron=FALSE,
                            command=lambda: folder_button_pressed(folder_button_variable)).pack(anchor='w', fill='x')

    def close_window(_=None):
        resend_interface.destroy()
        return

    close_button = Button(resend_interface_close_frame, text="Close", command=close_window)
    close_button.pack(pady=5)
    resend_interface.bind("<Escape>", close_window)

    resend_interface_files_list_count_spinbox = Spinbox(resend_interface_file_count_frame, from_=10, to=5000,
                                                        increment=5, width=4,
                                                        command=make_file_checkbutton_list)
    resend_interface_files_list_count_spinbox.delete(0, "end")
    resend_interface_files_list_count_spinbox.insert(0, 10)
    resend_interface_files_list_count_spinbox.configure(state=DISABLED)

    loading_label.destroy()
    resend_interface_file_count_frame.pack()
    Label(master=resend_interface_file_count_frame, text="File Limit:").pack(side=LEFT)
    resend_interface_files_list_count_spinbox.pack(side=RIGHT)
    Separator(master=resend_interface, orient=HORIZONTAL).pack(fill='x')
    resend_interface_scrollable_folders_frame.pack()
    resend_interface_scrollable_files_frame.pack()
    resend_interface_folders_frame.pack(side=LEFT)
    resend_interface_files_frame.pack(side=RIGHT)
    resend_interface_files_and_folders_frame.pack()
    Separator(master=resend_interface, orient=HORIZONTAL).pack(fill='x')
    resend_interface_close_frame.pack()
