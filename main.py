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
    folderstable.insert(dict(foldersname=folder, alias=tkSimpleDialog.askstring("Alias?", "Add Convenient Alias For" +
                                                                                "\n" + folder)))


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
    userslistframe = scrollbuttons.VerticalScrolledFrame(root)
    userslistframe.pack(side=RIGHT)
    for foldersname in folderstable.all():
        folderbuttonframe = Frame(userslistframe.interior)
        newdeletebuttonname = Button(folderbuttonframe, text="Delete",
                                     command=lambda name=foldersname['id']: delete_folder_entry(name))
        newbuttonname = Button(folderbuttonframe, text=foldersname['alias'],
                               command=lambda name=foldersname['id']: EditDialog(root, foldersname))
        newdeletebuttonname.pack(side=RIGHT)
        newbuttonname.pack(side=RIGHT)
        folderbuttonframe.pack()


class EditDialog(dialog.Dialog):

    def body(self, master):

        copytodirectory = None
        Label(master, text="Alias:").grid(row=0)
        Label(master, text="Backend?").grid(row=1)
        Label(master, text="Copy Destination?").grid(row=2)

        def select_copy_to_directory():
            global copytodirectory
            copytodirectory = str(askdirectory())

        self.e1 = Entry(master)
        self.e2 = Entry(master)
        self.e3 = Button(master, text="Select Folder", command=lambda: select_copy_to_directory())

        self.e1.grid(row=0, column=1)
        self.e2.grid(row=1, column=1)
        self.e3.grid(row=2, column=1)

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
        foldersnameapply['alias'] = str(self.e1.get())
        foldersnameapply['copy_to_directory'] = copytodirectory
        foldersnameapply['process_backend'] = str(self.e2.get())
        print (foldersnameapply)
        update_folder_alias(foldersnameapply)


def update_folder_alias(folderedit):
    folderstable.update(dict(alias=folderedit['alias'], id=folderedit['id'],
                             process_backend=folderedit['process_backend']), ['id'])
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
