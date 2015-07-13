from Tkinter import *
from tkFileDialog import askdirectory
import scrollbuttons
import dataset
import dialog
import dispatch
import os
import create_database

if not os.path.isfile('folders.db'):
    create_database.do()

database_connection = dataset.connect('sqlite:///folders.db')  # connect to database
folderstable = database_connection['folders']  # open table in database
oversight_and_defaults = database_connection['administrative']
root = Tk()  # create root window
root.title("Sender Interface")
folder = NONE
optionsframe = Frame(root)  # initialize left frame


def add_folder_entry():  # add unconfigured folder to database
    defaults = oversight_and_defaults.find_one(id=1)
    print (defaults)
    folderstable.insert(dict(foldersname=folder, is_active=defaults['is_active'],
                            alias=folder, process_backend=defaults['process_backend'], 
                             ftp_server=defaults['ftp_server'], 
                             ftp_folder=defaults['ftp_folder'],
                             ftp_username=defaults['ftp_username'], 
                             ftp_password=defaults['ftp_password'],
                             email_to=defaults['email_to'], 
                             email_origin_address=defaults['email_origin_address'], 
                             email_origin_username=defaults['email_origin_username'],
                             email_origin_password=defaults['email_origin_password'], 
                             email_origin_smtp_server=defaults['email_origin_smtp_server'],
                             process_edi=defaults['process_edi'], 
                             calc_upc=defaults['calc_upc'],
                             inc_arec=defaults['inc_arec'], 
                             inc_crec=defaults['inc_crec'], 
                             inc_headers=defaults['inc_headers'], 
                             filter_ampersand=defaults['filter_ampersand'],
                             pad_arec=defaults['pad_arec'],
                             arec_padding=defaults['arec_padding']))


def process_directories(folderstable_process):
    dispatch.process(folderstable_process)  # call dispatch module to process active folders


def select_folder():
    global folder
    global column_entry_value
    folder = askdirectory()
    column_entry_value = folder
    add_folder_entry()
    userslistframe.destroy()  # destroy lists on right
    make_users_list()  # recreate list


def make_users_list():
    global userslistframe
    global active_userslistframe
    global inactive_userslistframe
    userslistframe = Frame(root)
    active_users_list_container = Frame(userslistframe)
    inactive_users_list_container = Frame(userslistframe)
    active_userslistframe = scrollbuttons.VerticalScrolledFrame(active_users_list_container)
    inactive_userslistframe = scrollbuttons.VerticalScrolledFrame(inactive_users_list_container)
    active_users_list_label = Label(active_users_list_container, text="Active Users")  # active users title
    inactive_users_list_label = Label(inactive_users_list_container, text="Inactive Users")  # inactive users title
    # iterate over list of known folders, sorting into lists of active and inactive
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
    # pack widgets in correct order
    active_users_list_label.pack()
    inactive_users_list_label.pack()
    active_userslistframe.pack()
    inactive_userslistframe.pack()
    active_users_list_container.pack(side=RIGHT)
    inactive_users_list_container.pack(side=RIGHT)
    userslistframe.pack(side=RIGHT)


class EditDialog(dialog.Dialog):  # modal dialog for folder configuration.
    # note: this class makes no attempt to check correctness of input at the moment

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
        Label(master, text="FTP Server:").grid(row=6)
        Label(master, text="FTP Folder:").grid(row=7)
        Label(master, text="FTP Username:").grid(row=8)
        Label(master, text="FTP Password:").grid(row=9)
        Label(master, text="Email Backend Settings").grid(row=10)
        Label(master, text="Recipient Address:").grid(row=11)
        Label(master, text="Sender Address:").grid(row=12)
        Label(master, text="Sender Username:").grid(row=13)
        Label(master, text="Sender Password:").grid(row=14)
        Label(master, text="Sender Smtp Server:").grid(row=15)
        Label(master, text="Process EDI?").grid(row=0, column=3)
        Label(master, text="Calculate UPC Check Digit:").grid(row=1, column=3)
        Label(master, text="Include " + "A " + "Records:").grid(row=2, column=3)
        Label(master, text="Include " + "C " + "Records:").grid(row=3, column=3)
        Label(master, text="Include Headings:").grid(row=4, column=3)
        Label(master, text="Filter Ampersand:").grid(row=5, column=3)
        Label(master, text="Pad " + "A " + "Records:").grid(row=6, column=3)
        Label(master, text="A " + "Record Padding:").grid(row=7, column=3)

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
        self.e6 = Entry(master)
        self.e7 = Entry(master)
        self.e8 = Entry(master)
        self.e9 = Entry(master)
        self.e10 = Entry(master)
        self.e11 = Entry(master)
        self.e12 = Entry(master, show="*")
        self.e13 = Entry(master)
        self.e14 = Entry(master)
        self.e15 = Entry(master)
        self.e16 = Entry(master)
        self.e17 = Entry(master)
        self.e18 = Entry(master)
        self.e19 = Entry(master)
        self.e20 = Entry(master)
        self.e21 = Entry(master)

        self.e1.insert(0, self.foldersnameinput['is_active'])
        self.e2.insert(0, self.foldersnameinput['alias'])
        self.e3.insert(0, self.foldersnameinput['process_backend'])
        self.e5.insert(0, self.foldersnameinput['ftp_server'])
        self.e6.insert(0, self.foldersnameinput['ftp_folder'])
        self.e7.insert(0, self.foldersnameinput['ftp_username'])
        self.e8.insert(0, self.foldersnameinput['ftp_password'])
        self.e9.insert(0, self.foldersnameinput['email_to'])
        self.e10.insert(0, self.foldersnameinput['email_origin_address'])
        self.e11.insert(0, self.foldersnameinput['email_origin_username'])
        self.e12.insert(0, self.foldersnameinput['email_origin_password'])
        self.e13.insert(0, self.foldersnameinput['email_origin_smtp_server'])
        self.e14.insert(0, self.foldersnameinput['process_edi'])
        self.e15.insert(0, self.foldersnameinput['calc_upc'])
        self.e16.insert(0, self.foldersnameinput['inc_arec'])
        self.e17.insert(0, self.foldersnameinput['inc_crec'])
        self.e18.insert(0, self.foldersnameinput['inc_headers'])
        self.e19.insert(0, self.foldersnameinput['filter_ampersand'])
        self.e20.insert(0, self.foldersnameinput['pad_arec'])
        self.e21.insert(0, self.foldersnameinput['arec_padding'])

        self.e1.grid(row=0, column=1)
        self.e2.grid(row=1, column=1)
        self.e3.grid(row=2, column=1)
        self.e4.grid(row=4, column=1)
        self.e5.grid(row=6, column=1)
        self.e6.grid(row=7, column=1)
        self.e7.grid(row=8, column=1)
        self.e8.grid(row=9, column=1)
        self.e9.grid(row=11, column=1)
        self.e10.grid(row=12, column=1)
        self.e11.grid(row=13, column=1)
        self.e12.grid(row=14, column=1)
        self.e13.grid(row=15, column=1)
        self.e14.grid(row=0, column=4)
        self.e15.grid(row=1, column=4)
        self.e16.grid(row=2, column=4)
        self.e17.grid(row=3, column=4)
        self.e18.grid(row=4, column=4)
        self.e19.grid(row=5, column=4)
        self.e20.grid(row=6, column=4)
        self.e21.grid(row=7, column=4)

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
        foldersnameapply['ftp_server'] = str(self.e5.get())
        foldersnameapply['ftp_folder'] = str(self.e6.get())
        foldersnameapply['ftp_username'] = str(self.e7.get())
        foldersnameapply['ftp_password'] = str(self.e8.get())
        foldersnameapply['email_to'] = str(self.e9.get())
        foldersnameapply['email_origin_address'] = str(self.e10.get())
        foldersnameapply['email_origin_username'] = str(self.e11.get())
        foldersnameapply['email_origin_password'] = str(self.e12.get())
        foldersnameapply['email_origin_smtp_server'] = str(self.e13.get())
        foldersnameapply['process_edi'] = str(self.e14.get())
        foldersnameapply['calc_upc'] = str(self.e15.get())
        foldersnameapply['inc_arec'] = str(self.e16.get())
        foldersnameapply['inc_crec'] = str(self.e17.get())
        foldersnameapply['inc_headers'] = str(self.e18.get())
        foldersnameapply['filter_ampersand'] = str(self.e19.get())
        foldersnameapply['pad_arec'] = str(self.e20.get())
        foldersnameapply['arec_padding'] = str(self.e21.get())

        print (foldersnameapply)
        update_folder_alias(foldersnameapply)


def update_folder_alias(folderedit):  # update folder settings in database with results from EditDialog
    folderstable.update(folderedit, ['id'])
    refresh_users_list()

def refresh_users_list():
    userslistframe.destroy()
    make_users_list()

def delete_folder_entry(folder_to_be_removed):
    folderstable.delete(id=folder_to_be_removed)
    refresh_users_list()

def set_defaults_popup():
    defaults = oversight_and_defaults.find_one(id=1)
    EditDialog(root, defaults)

open_folder_button = Button(optionsframe, text="Open Directory", command=select_folder)
open_folder_button.pack(side=TOP)
process_folder_button = Button(optionsframe, text="Process Folders", command=lambda: process_directories(folderstable))
process_folder_button.pack(side=TOP)
default_settings = Button(optionsframe, text="Set Defaults", command=set_defaults_popup)
default_settings.pack(side=TOP)
optionsframe.pack(side=LEFT)

make_users_list()

root.mainloop()
