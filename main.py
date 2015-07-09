from Tkinter import *
from tkFileDialog import askdirectory
import scrollbuttons
import dataset
import tkSimpleDialog
import dialog

database_connection = dataset.connect('sqlite:///folders.db')
folderstable = database_connection['folders']
root = Tk()
root.title("Sender Interface")
folder = NONE
optionsframe = Frame(root)


def add_folder_entry():
    folderstable.insert(dict(foldersname=folder, alias=tkSimpleDialog.askstring("Alias?", "Add Convenient Alias For" +
                                                                                "\n" + folder)))


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
                                     command=lambda name=foldersname['foldersname']: delete_folder_entry(name))
        newbuttonname = Button(folderbuttonframe, text=foldersname['alias'],
                               command=lambda name=foldersname['foldersname']: editdialog(root, foldersname))
        newdeletebuttonname.pack(side=RIGHT)
        newbuttonname.pack(side=RIGHT)
        folderbuttonframe.pack()


def list_entry(selected_folder):
    print(selected_folder)
    foldername = folderstable.find_one(foldersname=selected_folder)
    print (foldername['alias'])
    print (foldername['id'])


class editdialog(dialog.Dialog):

    def body(self, master):

        Label(master, text="Alias:").grid(row=0)

        self.e1 = Entry(master)

        self.e1.grid(row=0, column=1)

        return self.e1 # initial focus

    def apply(self, foldersnameapply):
        first = str(self.e1.get())
        foldersnameapply['alias'] = str(self.e1.get())
        print (foldersnameapply)
        update_folder_alias(foldersnameapply)


def update_folder_alias(folderedit):
    folderstable.update(dict(alias=folderedit['alias'], id=folderedit['id']), ['id'])
    userslistframe.destroy()
    make_users_list()


def delete_folder_entry(folder_to_be_removed):
    folderstable.delete(foldersname=folder_to_be_removed)
    userslistframe.destroy()
    make_users_list()


open_folder_button = Button(optionsframe, text="Open Directory", command=select_folder)
open_folder_button.pack(side=TOP)
optionsframe.pack(side=LEFT)

make_users_list()

root.mainloop()
