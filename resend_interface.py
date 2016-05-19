from tkinter import *
from tkinter.ttk import *
import tkinter
from tkinter.messagebox import showerror
import scrollbuttons
import os
from operator import itemgetter


def do(database_connection, master_window):
    processed_files_table = database_connection['processed_files']
    if processed_files_table.count() == 0:
        showerror(message="Nothing To Configure")
        return
    configured_folders_table = database_connection['folders']
    folder_list = []
    folder_button_variable = IntVar()
    resend_interface = Toplevel()
    resend_interface.title("Enable Resend")
    resend_interface.transient(master_window)
    resend_interface.geometry("+%d+%d" % (master_window.winfo_rootx() + 50, master_window.winfo_rooty() + 50))
    resend_interface.grab_set()
    resend_interface.focus_set()
    resend_interface.resizable(width=FALSE, height=FALSE)
    resend_interface_files_and_folders_frame = Frame(resend_interface)
    resend_interface_folders_frame = Frame(resend_interface_files_and_folders_frame)
    resend_interface_files_frame = Frame(resend_interface_files_and_folders_frame)
    resend_interface_close_frame = Frame(resend_interface)

    def set_resend_flag(identifier, resend_flag):
        processed_files_update = dict(dict(resend_flag=resend_flag, id=identifier))
        processed_files_table.update(processed_files_update, ['id'])

    def folder_button_pressed(button):
        for child in resend_interface_scrollable_files_frame.interior.winfo_children():
            child.destroy()
        file_list = []
        file_name_list = []
        for processed_line in processed_files_table.find(folder_id=button.get(), order_by="-sent_date_time"):
            if processed_line['file_name'] not in file_name_list and os.path.exists(processed_line['file_name']):
                file_list.append([processed_line['file_name'], processed_line['resend_flag'], processed_line['id']])
                file_name_list.append(processed_line['file_name'])
            if len(file_list) == 10:
                break
        for file_name, resend_flag, identifier in file_list:
            CheckButtons(resend_interface_scrollable_files_frame.interior, file_name, resend_flag, identifier)

    class CheckButtons:
        def __init__(self, master, file_name, resend_flag, identifier):
            self.identifier = identifier
            self.resend_flag = resend_flag
            self.file_name = file_name
            self.var = BooleanVar()
            self.var.set(self.resend_flag)
            c = Checkbutton(master=master,
                            text=os.path.basename(file_name).ljust(15),
                            variable=self.var,
                            onvalue=True,
                            offvalue=False,
                            command=self.cb)
            c.pack(anchor="e", fill=X)

        def cb(self):
            set_resend_flag(self.identifier, self.var.get())

    loading_label = Label(master=resend_interface, text="Loading...")
    loading_label.pack()
    master_window.update()

    for line in processed_files_table.distinct('folder_id'):
        folder_alias = configured_folders_table.find_one(id=line['folder_id'])
        folder_list.append([line['folder_id'], folder_alias['alias']])
    sorted_folder_list = sorted(folder_list, key=itemgetter(1))

    resend_interface_scrollable_folders_frame = scrollbuttons.VerticalScrolledFrame(resend_interface_folders_frame)
    resend_interface_scrollable_files_frame = scrollbuttons.VerticalScrolledFrame(resend_interface_files_frame)
    Label(master=resend_interface_scrollable_files_frame.interior, text="Select a Folder.").pack()

    for folder, alias in sorted_folder_list:
        tkinter.Radiobutton(resend_interface_scrollable_folders_frame.interior, text=alias.rjust(15),
                            variable=folder_button_variable,
                            value=folder, indicatoron=FALSE,
                            command=lambda: folder_button_pressed(folder_button_variable)).pack(anchor='w', fill='x')

    def close_window(_=None):
        resend_interface.destroy()
        return

    close_button = Button(resend_interface_close_frame, text="Close", command=close_window)
    close_button.pack(pady=5)
    resend_interface.bind("<Escape>", close_window)

    loading_label.destroy()
    resend_interface_scrollable_folders_frame.pack()
    resend_interface_scrollable_files_frame.pack()
    resend_interface_folders_frame.pack(side=LEFT)
    resend_interface_files_frame.pack(side=RIGHT)
    resend_interface_files_and_folders_frame.pack()
    resend_interface_close_frame.pack()
