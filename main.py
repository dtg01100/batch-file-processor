from Tkinter import *
from tkFileDialog import askdirectory
from ttk import *
from validate_email import validate_email
import scrollbuttons
import dataset
import dialog
import dispatch
import os
import create_database
import time
import datetime
import batch_log_sender
import print_run_log
import argparse
import sqlalchemy.dialects.sqlite  # needed for py2exe


if not os.path.isfile('folders.db'):
    create_database.do()

database_connection = dataset.connect('sqlite:///folders.db')  # connect to database
folderstable = database_connection['folders']  # open table in database
emails_table = database_connection['emails_to_send']
sent_emails_removal_queue = database_connection['sent_emails_removal_queue']
oversight_and_defaults = database_connection['administrative']
launch_options = argparse.ArgumentParser()
root = Tk()  # create root window
root.title("Sender Interface")
folder = NONE
optionsframe = Frame(root)  # initialize left frame

logs_directory = oversight_and_defaults.find_one(id=1)
if not os.path.isdir(logs_directory['logs_directory']):
    os.mkdir(logs_directory['logs_directory'])


def add_folder_entry(folder):  # add unconfigured folder to database
    defaults = oversight_and_defaults.find_one(id=1)
    print (defaults)
    folder_alias_constructor = os.path.basename(folder)
    folderstable.insert(dict(foldersname=folder, is_active=defaults['is_active'],
                             alias=folder_alias_constructor, process_backend=defaults['process_backend'],
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
                             arec_padding=defaults['arec_padding'],
                             email_smtp_port=defaults['email_smtp_port'],
                             reporting_smtp_port=defaults['reporting_smtp_port'],
                             ftp_port=defaults['ftp_port']))


def select_folder():
    global folder
    global column_entry_value
    folder = askdirectory()
    if folder != '':
        column_entry_value = folder
        add_folder_entry(folder)
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
    if folderstable.count(is_active="True") == 0:
        no_active_label = Label(active_userslistframe, text="No Active Folders")
        no_active_label.pack()
    if folderstable.count(is_active="False") == 0:
        no_inactive_label = Label(inactive_userslistframe, text="No Inactive Folders")
        no_inactive_label.pack()
    # iterate over list of known folders, sorting into lists of active and inactive
    for foldersname in folderstable.all():
        if str(foldersname['is_active']) != "False":
            active_folderbuttonframe = Frame(active_userslistframe.interior)
            buttonlabelstring = ('..' + foldersname['alias'][75:]) if len(foldersname['alias']) > 75 else foldersname['alias']
            Button(active_folderbuttonframe, text="Delete",
                   command=lambda name=foldersname['id']: delete_folder_entry(name)).grid(column=1, row=0, sticky=E)
            Button(active_folderbuttonframe, text=buttonlabelstring,
                   command=lambda name=foldersname['id']: EditDialog(root, foldersname)).grid(column=0, row=0, sticky=E)
            active_folderbuttonframe.pack(anchor='e')
        else:
            inactive_folderbuttonframe = Frame(inactive_userslistframe.interior)
            buttonlabelstring = ('..' + foldersname['alias'][75:]) if len(foldersname['alias']) > 75 else foldersname['alias']
            Button(inactive_folderbuttonframe, text="Delete",
                   command=lambda name=foldersname['id']: delete_folder_entry(name)).grid(column=1, row=0, sticky=E)
            Button(inactive_folderbuttonframe, text=buttonlabelstring,
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


class EditReportingDialog(dialog.Dialog):  # modal dialog for folder configuration.

    def body(self, master):

        global logs_directory_edit
        logs_directory_edit = None
        global logs_directory_is_altered
        logs_directory_is_altered = False
        self.enable_reporting_checkbutton = StringVar(master)
        self.enable_report_printing_checkbutton = StringVar(master)

        Label(master, text="Enable Report Sending:").grid(row=0, sticky=E)
        Label(master, text="Reporting Email Address:").grid(row=1, sticky=E)
        Label(master, text="Reporting Email Username:").grid(row=2, sticky=E)
        Label(master, text="Reporting Email Password:").grid(row=3, sticky=E)
        Label(master, text="Reporting Email SMTP Server:").grid(row=4, sticky=E)
        Label(master, text="Reporting Email SMTP Port").grid(row=5, sticky=E)
        Label(master, text="Reporting Email Destination:").grid(row=6, sticky=E)
        Label(master, text="Log File Folder").grid(row=7, sticky=E)
        Label(master, text="Enable Report Printing Fallback:").grid(row=8, sticky=E)

        self.e0 = Checkbutton(master, variable=self.enable_reporting_checkbutton, onvalue="True", offvalue="False")
        self.e1 = Entry(master)
        self.e2 = Entry(master)
        self.e3 = Entry(master, show="*")
        self.e4 = Entry(master)
        self.e5 = Entry(master)
        self.e6 = Entry(master)
        self.e7 = Button(master, text="Select Folder", command=lambda: select_log_directory())
        self.e8 = Checkbutton(master, variable=self.enable_report_printing_checkbutton, onvalue="True", offvalue="False")

        def select_log_directory():
            global logs_directory_edit
            global logs_directory_is_altered
            logs_directory_edit = str(askdirectory())
            logs_directory_is_altered = True

        self.enable_reporting_checkbutton.set(self.foldersnameinput['enable_reporting'])
        self.e1.insert(0, self.foldersnameinput['report_email_address'])
        self.e2.insert(0, self.foldersnameinput['report_email_username'])
        self.e3.insert(0, self.foldersnameinput['report_email_password'])
        self.e4.insert(0, self.foldersnameinput['report_email_smtp_server'])
        self.e5.insert(0, self.foldersnameinput['reporting_smtp_port'])
        self.e6.insert(0, self.foldersnameinput['report_email_destination'])
        self.enable_report_printing_checkbutton.set(self.foldersnameinput['report_printing_fallback'])

        self.e0.grid(row=0, column=1)
        self.e1.grid(row=1, column=1)
        self.e2.grid(row=2, column=1)
        self.e3.grid(row=3, column=1)
        self.e4.grid(row=4, column=1)
        self.e5.grid(row=5, column=1)
        self.e6.grid(row=6, column=1)
        self.e7.grid(row=7, column=1)
        self.e8.grid(row=8, column=1)

        return self.e1  # initial focus

    def validate(self):

        if self.enable_reporting_checkbutton.get() == "True":
            if (validate_email(str(self.e1.get()), verify=True)) is False:
                return False
            if (validate_email(str(self.e2.get()), verify=True)) is False:
                return False
            if (validate_email(str(self.e6.get()), verify=True)) is False:
                return False
        return 1

    def ok(self, event=None):

        if not self.validate():
            self.initial_focus.focus_set()  # put focus back
            return

        self.withdraw()
        self.update_idletasks()

        self.apply(self.foldersnameinput)

        self.cancel()

    def apply(self, foldersnameapply):

        global logs_directory_edit
        global logs_directory_is_altered

        foldersnameapply['enable_reporting'] = str(self.enable_reporting_checkbutton.get())
        if logs_directory_is_altered is True:
            foldersnameapply['log_directory'] = logs_directory_edit
        foldersnameapply['report_email_address'] = str(self.e1.get())
        foldersnameapply['report_email_username'] = str(self.e2.get())
        foldersnameapply['report_email_password'] = str(self.e3.get())
        foldersnameapply['report_email_smtp_server'] = str(self.e4.get())
        foldersnameapply['reporting_smtp_port'] = str(self.e5.get())
        foldersnameapply['report_email_destination'] = str(self.e6.get())

        print (foldersnameapply)
        update_reporting(foldersnameapply)


class EditDialog(dialog.Dialog):  # modal dialog for folder configuration.

    def body(self, master):

        global copytodirectory
        copytodirectory = None
        global destination_directory_is_altered
        destination_directory_is_altered = False
        self.backendvariable = StringVar(master)
        self.active_checkbutton = StringVar(master)
        self.process_edi = StringVar(master)
        self.upc_var_check = StringVar(master)  # define  "UPC calculation" checkbox state variable
        self.a_rec_var_check = StringVar(master)  # define "A record checkbox state variable
        self.c_rec_var_check = StringVar(master)  # define "C record" checkbox state variable
        self.c_headers_check = StringVar(master)  # define "Column Headers" checkbox state variable
        self.ampersand_check = StringVar(master)  # define "Filter Ampersand" checkbox state variable
        self.pad_arec_check = StringVar(master)
        Label(master, text="Active?").grid(row=0, sticky=E)
        if self.foldersnameinput['foldersname'] != 'template':
            Label(master, text="Alias:").grid(row=1, sticky=E)
        Label(master, text="Backend?").grid(row=2, sticky=E)
        Label(master, text="Copy Backend Settings").grid(row=3, sticky=E)
        Label(master, text="Copy Destination?").grid(row=4, sticky=E)
        Label(master, text="Ftp Backend Settings").grid(row=5, sticky=E)
        Label(master, text="FTP Server:").grid(row=6, sticky=E)
        Label(master, text="FTP Port:").grid(row=7, sticky=E)
        Label(master, text="FTP Folder:").grid(row=8, sticky=E)
        Label(master, text="FTP Username:").grid(row=9, sticky=E)
        Label(master, text="FTP Password:").grid(row=10, sticky=E)
        Label(master, text="Email Backend Settings").grid(row=11, sticky=E)
        Label(master, text="Recipient Address:").grid(row=12, sticky=E)
        Label(master, text="Sender Address:").grid(row=13, sticky=E)
        Label(master, text="Sender Username:").grid(row=14, sticky=E)
        Label(master, text="Sender Password:").grid(row=15, sticky=E)
        Label(master, text="Sender SMTP Server:").grid(row=16, sticky=E)
        Label(master, text="SMTP Server Port:").grid(row=17, sticky=E)
        Label(master, text="Process EDI?").grid(row=0, column=3, sticky=E)
        Label(master, text="Calculate UPC Check Digit:").grid(row=1, column=3, sticky=E)
        Label(master, text="Include " + "A " + "Records:").grid(row=2, column=3, sticky=E)
        Label(master, text="Include " + "C " + "Records:").grid(row=3, column=3, sticky=E)
        Label(master, text="Include Headings:").grid(row=4, column=3, sticky=E)
        Label(master, text="Filter Ampersand:").grid(row=5, column=3, sticky=E)
        Label(master, text="Pad " + "A " + "Records:").grid(row=6, column=3, sticky=E)
        Label(master, text="A " + "Record Padding (6 characters):").grid(row=7, column=3, sticky=E)

        def select_copy_to_directory():
            global copytodirectory
            global destination_directory_is_altered
            copytodirectory = str(askdirectory())
            destination_directory_is_altered = True

        self.e1 = Checkbutton(master, variable=self.active_checkbutton, onvalue="True", offvalue="False")
        if self.foldersnameinput['foldersname'] != 'template':
            self.e2 = Entry(master)
        self.e3 = OptionMenu(master, self.backendvariable, "none", "copy", "ftp", "email")
        self.e4 = Button(master, text="Select Folder", command=lambda: select_copy_to_directory())
        self.e5 = Entry(master)
        self.e6 = Entry(master)
        self.e7 = Entry(master)
        self.e8 = Entry(master)
        self.e9 = Entry(master, show="*")
        self.e10 = Entry(master)
        self.e11 = Entry(master)
        self.e12 = Entry(master)
        self.e13 = Entry(master, show="*")
        self.e14 = Entry(master)
        self.e15 = Entry(master)
        self.e16 = Checkbutton(master, variable=self.process_edi, onvalue="True", offvalue="False")
        self.e17 = Checkbutton(master, variable=self.upc_var_check, onvalue="True", offvalue="False")
        self.e18 = Checkbutton(master, variable=self.a_rec_var_check, onvalue="True", offvalue="False")
        self.e19 = Checkbutton(master, variable=self.c_rec_var_check, onvalue="True", offvalue="False")
        self.e20 = Checkbutton(master, variable=self.c_headers_check, onvalue="True", offvalue="False")
        self.e21 = Checkbutton(master, variable=self.ampersand_check, onvalue="True", offvalue="False")
        self.e22 = Checkbutton(master, variable=self.pad_arec_check, onvalue="True", offvalue="False")
        self.e23 = Entry(master)

        self.active_checkbutton.set(self.foldersnameinput['is_active'])
        if self.foldersnameinput['foldersname'] != 'template':
            self.e2.insert(0, self.foldersnameinput['alias'])
        self.backendvariable.set(self.foldersnameinput['process_backend'])
        self.e5.insert(0, self.foldersnameinput['ftp_server'])
        self.e6.insert(0, self.foldersnameinput['ftp_port'])
        self.e7.insert(0, self.foldersnameinput['ftp_folder'])
        self.e8.insert(0, self.foldersnameinput['ftp_username'])
        self.e9.insert(0, self.foldersnameinput['ftp_password'])
        self.e10.insert(0, self.foldersnameinput['email_to'])
        self.e11.insert(0, self.foldersnameinput['email_origin_address'])
        self.e12.insert(0, self.foldersnameinput['email_origin_username'])
        self.e13.insert(0, self.foldersnameinput['email_origin_password'])
        self.e14.insert(0, self.foldersnameinput['email_origin_smtp_server'])
        self.e15.insert(0, self.foldersnameinput['email_smtp_port'])
        self.process_edi.set(self.foldersnameinput['process_edi'])
        self.upc_var_check.set(self.foldersnameinput['calc_upc'])
        self.a_rec_var_check.set(self.foldersnameinput['inc_arec'])
        self.c_rec_var_check.set(self.foldersnameinput['inc_crec'])
        self.c_headers_check.set(self.foldersnameinput['inc_headers'])
        self.ampersand_check.set(self.foldersnameinput['filter_ampersand'])
        self.pad_arec_check.set(self.foldersnameinput['pad_arec'])
        self.e23.insert(0, self.foldersnameinput['arec_padding'])

        self.e1.grid(row=0, column=1)
        if self.foldersnameinput['foldersname'] != 'template':
            self.e2.grid(row=1, column=1)
        self.e3.grid(row=2, column=1)
        self.e4.grid(row=4, column=1)
        self.e5.grid(row=6, column=1)
        self.e6.grid(row=7, column=1)
        self.e7.grid(row=8, column=1)
        self.e8.grid(row=9, column=1)
        self.e9.grid(row=10, column=1)
        self.e10.grid(row=12, column=1)
        self.e11.grid(row=13, column=1)
        self.e12.grid(row=14, column=1)
        self.e13.grid(row=15, column=1)
        self.e14.grid(row=16, column=1)
        self.e15.grid(row=17, column=1)
        self.e16.grid(row=0, column=4)
        self.e17.grid(row=1, column=4)
        self.e18.grid(row=2, column=4)
        self.e19.grid(row=3, column=4)
        self.e20.grid(row=4, column=4)
        self.e21.grid(row=5, column=4)
        self.e22.grid(row=6, column=4)
        self.e23.grid(row=7, column=4)

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
        foldersnameapply['is_active'] = str(self.active_checkbutton.get())
        if self.foldersnameinput['foldersname'] != 'template':
            if str(self.e2.get()) == '':
                foldersnameapply['alias'] = os.path.basename(self.foldersnameinput['foldersname'])
            else:
                foldersnameapply['alias'] = str(self.e2.get())
        if destination_directory_is_altered is True:
            foldersnameapply['copy_to_directory'] = copytodirectory
        foldersnameapply['process_backend'] = str(self.backendvariable.get())
        foldersnameapply['ftp_server'] = str(self.e5.get())
        foldersnameapply['ftp_port'] = str(self.e6.get())
        foldersnameapply['ftp_folder'] = str(self.e7.get())
        foldersnameapply['ftp_username'] = str(self.e8.get())
        foldersnameapply['ftp_password'] = str(self.e9.get())
        foldersnameapply['email_to'] = str(self.e10.get())
        foldersnameapply['email_origin_address'] = str(self.e11.get())
        foldersnameapply['email_origin_username'] = str(self.e12.get())
        foldersnameapply['email_origin_password'] = str(self.e13.get())
        foldersnameapply['email_origin_smtp_server'] = str(self.e14.get())
        foldersnameapply['process_edi'] = str(self.process_edi.get())
        foldersnameapply['calc_upc'] = str(self.upc_var_check.get())
        foldersnameapply['inc_arec'] = str(self.a_rec_var_check.get())
        foldersnameapply['inc_crec'] = str(self.c_rec_var_check.get())
        foldersnameapply['inc_headers'] = str(self.c_headers_check.get())
        foldersnameapply['filter_ampersand'] = str(self.ampersand_check.get())
        foldersnameapply['pad_arec'] = str(self.pad_arec_check.get())
        foldersnameapply['arec_padding'] = str(self.e23.get())

        print (foldersnameapply)
        update_folder_alias(foldersnameapply)

    def validate(self):

        if str(self.backendvariable.get()) == "email":
            if (validate_email(str(self.e11.get()), verify=True)) is False:
                return False

            if (validate_email(str(self.e10.get()), verify=True)) is False:
                return False

        if len(str(self.e23.get())) is not 6 and str(self.pad_arec_check.get()) == "True":
            return False

        return 1


def update_reporting(changes):
    oversight_and_defaults.update(changes, ['id'])


def update_folder_alias(folderedit):  # update folder settings in database with results from EditDialog
    folderstable.update(folderedit, ['id'])
    refresh_users_list()


def refresh_users_list():
    userslistframe.destroy()
    make_users_list()


def delete_folder_entry(folder_to_be_removed):
    folderstable.delete(id=folder_to_be_removed)
    refresh_users_list()


def graphical_process_directories(folderstable_process):
    process_directories(folderstable_process)
    refresh_users_list()


def set_defaults_popup():
    defaults = oversight_and_defaults.find_one(id=1)
    EditDialog(root, defaults)


def process_directories(folderstable_process):
    global emails_table
    start_time = str(datetime.datetime.now())
    reporting = oversight_and_defaults.find_one(id=1)
    run_log_name_constructor = "Run Log " + str(time.ctime()).replace(":", "-") + ".txt"
    run_log_fullpath = os.path.join(reporting['logs_directory'], run_log_name_constructor)
    print (run_log_fullpath)
    run_log = open(run_log_fullpath, 'w')
    run_log.write("starting run at " + time.ctime() + "\r\n")
    # call dispatch module to process active folders
    try:
        dispatch.process(folderstable_process, run_log, emails_table)
    except Exception, error:
        print("Run failed, check your configuration \r\nError from dispatch module is: \r\n" + str(error) + "\r\n")
        run_log.write(
            "Run failed, check your configuration \r\nError from dispatch module is: \r\n" + str(error) + "\r\n")
    emails_table.insert(dict(log=run_log_fullpath, folder_alias=run_log_name_constructor))
    run_log.close()
    if reporting['enable_reporting'] == "True":
        try:
            sent_emails_removal_queue.delete()
            batch_log_sender.do(reporting, emails_table, sent_emails_removal_queue, start_time)
            for line in sent_emails_removal_queue.all():
                emails_table.delete(log=str(line['log']))
            sent_emails_removal_queue.delete()
        except Exception, error:
            run_log = open(run_log_fullpath, 'a')
            print("Emailing report log failed with: " + str(error) + ", printing file\r\n")
            run_log.write("Emailing report log failed with: " + str(error) + ", printing file\r\n")
            run_log.close()
            if reporting['report_printing_fallback'] == "True":
                try:
                    run_log = open(run_log_fullpath, 'r')
                    print_run_log.do(run_log)
                    run_log.close()
                except Exception, error:
                    print("printing error log failed with error: " + str(error) + "\r\n")
                    run_log = open(run_log_fullpath, 'a')
                    run_log.write("Printing error log failed with error: " + str(error) + "\r\n")
                    run_log.close()
            else:
                run_log = open(run_log_fullpath, 'a')
                run_log.write("Report printing fallback disabled")
                run_log.close()


def silent_process_directories(folderstable):
    print "batch processing configured directories"
    process_directories(folderstable)
    quit()


launch_options.add_argument('--automatic', action='store_true')
args = launch_options.parse_args()
if args.automatic:
    silent_process_directories(folderstable)

open_folder_button = Button(optionsframe, text="Add Directory", command=select_folder)
open_folder_button.pack(side=TOP, fill=X)
default_settings = Button(optionsframe, text="Set Defaults", command=set_defaults_popup)
default_settings.pack(side=TOP, fill=X)
reporting_options = oversight_and_defaults.find_one(id=1)
edit_reporting = Button(optionsframe, text="Edit Reporting",
                        command=lambda: EditReportingDialog(root, reporting_options))
edit_reporting.pack(side=TOP, fill=X)
process_folder_button = Button(optionsframe, text="Process Folders", command=lambda: graphical_process_directories(folderstable))
process_folder_button.pack(side=TOP, fill=X)
optionsframe.pack(side=LEFT)

make_users_list()

root.mainloop()
