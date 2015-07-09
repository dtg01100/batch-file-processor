from Tkinter import *
from tkFileDialog import askdirectory
import scrollbuttons
import dataset
import tkSimpleDialog
import dialog
import dispatch

database_connection = dataset.connect('sqlite:///folders.db')
folderstable = database_connection['folders']
root = Tk()
root.title("Sender Interface")
folder = NONE
optionsframe = Frame(root)


def add_folder_entry():
    folderstable.insert(dict(foldersname=folder, is_active="False",
                             alias=folder, process_backend='null'))


def process_directories(folderstable_process):
    dispatch.process(folderstable_process)


def select_folder():
    global folder
    global column_entry_value
    folder = askdirectory()
    column_entry_value = folder
    add_folder_entry()
    userslistframe.destroy()
    make_users_list()


def make_users_list():
    global userslistframe
    global active_userslistframe
    global inactive_userslistframe
    userslistframe = Frame(root)
    active_users_list_container = Frame(userslistframe)
    inactive_users_list_container = Frame(userslistframe)
    active_userslistframe = scrollbuttons.VerticalScrolledFrame(active_users_list_container)
    inactive_userslistframe = scrollbuttons.VerticalScrolledFrame(inactive_users_list_container)
    active_users_list_label = Label(active_users_list_container, text="Active Users")
    inactive_users_list_label = Label(inactive_users_list_container, text="Inactive Users")
    for foldersname in folderstable.all():
        if str(foldersname['is_active']) != "False":
            active_folderbuttonframe = Frame(active_userslistframe.interior)
            Button(active_folderbuttonframe, text="Delete",
                                         command=lambda name=foldersname['id']: delete_folder_entry(name)).grid(column=1, row=0, sticky=E)
            Button(active_folderbuttonframe, text=foldersname['alias'],
                                   command=lambda name=foldersname['id']: EditDialog(root, foldersname)).grid(column=0, row=0, sticky=E)
            active_folderbuttonframe.pack(anchor='e')
        else:
            inactive_folderbuttonframe = Frame(inactive_userslistframe.interior)
            Button(inactive_folderbuttonframe, text="Delete",
                                         command=lambda name=foldersname['id']: delete_folder_entry(name)).grid(column=1, row=0, sticky=E)
            Button(inactive_folderbuttonframe, text=foldersname['alias'],
                                   command=lambda name=foldersname['id']: EditDialog(root, foldersname)).grid(column=0, row=0, sticky=E)
            inactive_folderbuttonframe.pack(anchor='e')
    active_users_list_label.pack()
    inactive_users_list_label.pack()
    active_userslistframe.pack()
    inactive_userslistframe.pack()
    active_users_list_container.pack(side=RIGHT)
    inactive_users_list_container.pack(side=RIGHT)
    userslistframe.pack(side=RIGHT)

class EditDialog(dialog.Dialog):

    def body(self, master):

        global copytodirectory
        copytodirectory = None
        global destination_directory_is_altered
        destination_directory_is_altered = False
        Label(master, text="Active?").grid(row=0)
        Label(master, text="Alias:").grid(row=1)
        Label(master, text="Backend?").grid(row=2)
        Label(master, text="Copy Backend Settings").grid(row=3)
        Label(master, text="Copy Destination?").grid(row=4)
        Label(master, text="Ftp Backend Settings").grid(row=5)


        def select_copy_to_directory():
            global copytodirectory
            global destination_directory_is_altered
            copytodirectory = str(askdirectory())
            destination_directory_is_altered = True

        self.e1 = Entry(master)
        self.e2 = Entry(master)
        self.e3 = Entry(master)
        self.e4 = Button(master, text="Select Folder", command=lambda: select_copy_to_directory())
        self.e5 = Entry(master)

        self.e1.insert(0, self.foldersnameinput['is_active'])
        self.e2.insert(0, self.foldersnameinput['alias'])
        self.e3.insert(0, self.foldersnameinput['process_backend'])
        self.e1.grid(row=0, column=1)
        self.e2.grid(row=1, column=1)
        self.e3.grid(row=2, column=1)
        self.e4.grid(row=4, column=1)

        return self.e1  # initial focus

    def ok(self, event=None):

        if not self.validate():
            self.initial_focus.focus_set()  # put focus back
            return

        self.withdraw()
        self.update_idletasks()

        self.apply(self.foldersnameinput)

        self.cancel()

    def apply(self, foldersnameapply):
        global copytodirectory
        global destination_directory_is_altered
        foldersnameapply['is_active'] = str(self.e1.get())
        foldersnameapply['alias'] = str(self.e2.get())
        if destination_directory_is_altered is True:
            foldersnameapply['copy_to_directory'] = copytodirectory
        foldersnameapply['process_backend'] = str(self.e3.get())
        print (foldersnameapply)
        update_folder_alias(foldersnameapply)


def update_folder_alias(folderedit):
    folderstable.update(folderedit, ['id'])
    userslistframe.destroy()
    make_users_list()


def delete_folder_entry(folder_to_be_removed):
    folderstable.delete(id=folder_to_be_removed)
    userslistframe.destroy()
    make_users_list()


open_folder_button = Button(optionsframe, text="Open Directory", command=select_folder)
open_folder_button.pack(side=TOP)
process_folder_button = Button(optionsframe, text="Process Folders", command=lambda: process_directories(folderstable))
process_folder_button.pack(side=TOP)
optionsframe.pack(side=LEFT)

make_users_list()

root.mainloop()
