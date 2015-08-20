version = "1.0 rc2"
database_version = "1"
print("Batch Log Sender Version " + version)
try:  # try to import required modules
    from Tkinter import *
    from tkFileDialog import askdirectory
    from tkMessageBox import showerror
    from tkMessageBox import showinfo
    from tkMessageBox import askokcancel
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
    import cStringIO
    import shutil
    import doing_stuff_overlay
    from tendo import singleton
except Exception, error:
    try:  # if importing doesn't work, not much to do other than log and quit
        print(str(error))
        critical_log = open("critical_error.log", 'a')
        critical_log.write("program version is " + version)
        critical_log.write(str(error) + "\r\n")
        critical_log.close()
        raise SystemExit
    except Exception, big_error:  # if logging doesn't work, at least complain
        print("error writing critical error log for error: " + str(error) + "\n" + "operation failed with error: " + str(big_error))
        raise SystemExit


# prevent multiple instances from running
me = singleton.SingleInstance()

if not os.path.isfile('folders.db'):  # if the database file is missing
    try:
        print("creating initial database file...")
        creating_database_popup = Tk()
        Label(creating_database_popup, text="Creating initial database file...").pack()
        creating_database_popup.update()
        create_database.do(database_version)  # make a new one
        print("done")
        creating_database_popup.destroy()
    except Exception, error:  # if that doesn't work for some reason, log and quit
        try:
            print(str(error))
            critical_log = open("critical_error.log", 'a')
            critical_log.write("program version is " + version)
            critical_log.write(str(datetime.datetime.now()) + str(error) + "\r\n")
            critical_log.close()
            raise SystemExit
        except Exception, big_error:  # if logging doesn't work, at least complain
            print("error writing critical error log for error: " + str(error) + "\n" + "operation failed with error: " + str(big_error))
            raise SystemExit

try:  # try to connect to database
    database_connection = dataset.connect('sqlite:///folders.db')  # connect to database
except Exception, error:  # if that doesn't work for some reason, log and quit
    try:
        print(str(error))
        critical_log = open("critical_error.log", 'a')
        critical_log.write("program version is " + version)
        critical_log.write(str(datetime.datetime.now()) + str(error) + "\r\n")
        critical_log.close()
        raise SystemExit
    except Exception, big_error:  # if logging doesn't work, at least complain
        print("error writing critical error log for error: " + str(error) + "\n" + "operation failed with error: " + str(big_error))
        raise SystemExit

# open table required for database check in database
db_version = database_connection['version']
db_version_dict = db_version.find_one(id=1)
if db_version_dict['version'] != database_version:
    Tk().withdraw()
    showerror(title="Database Mismatch", message="Database version mismatch\ndatabase version is: " + str(db_version_dict['version']) + "\ndatabase version expected is: " + str(database_version))
    raise SystemExit

# open required tables in database
folderstable = database_connection['folders']
emails_table = database_connection['emails_to_send']
emails_table_batch = database_connection['working_batch_emails_to_send']
sent_emails_removal_queue = database_connection['sent_emails_removal_queue']
oversight_and_defaults = database_connection['administrative']
obe_queue = database_connection['obe_queue']
launch_options = argparse.ArgumentParser()
root = Tk()  # create root window
root.title("Sender Interface " + version)
folder = NONE
optionsframe = Frame(root)  # initialize left frame
logs_directory = oversight_and_defaults.find_one(id=1)


def check_logs_directory():
    try:
        # check to see if log directory is writable
        test_log_file = open(os.path.join(logs_directory['logs_directory'], 'test_log_file'), 'w')
        test_log_file.close()
        os.remove(os.path.join(logs_directory['logs_directory'], 'test_log_file'))
    except IOError, error:
        print(str(error))
        return False


def add_folder_entry(folder):  # add folder to database, copying configuration from template
    defaults = oversight_and_defaults.find_one(id=1)
    folder_alias_constructor = os.path.basename(folder)

    def folder_alias_checker(check):
        # check database to see if the folder alias exists, and return false if it does
        proposed_folder = folderstable.find_one(alias=check)
        if proposed_folder is not None:
            return False
    if folder_alias_checker(folder_alias_constructor) is False:
        # auto generate a number to add to automatic aliases
        folder_alias_end_suffix = 0
        folder_alias_deduplicate_constructor = folder_alias_constructor
        while folder_alias_checker(folder_alias_deduplicate_constructor) is False:
            folder_alias_end_suffix += folder_alias_end_suffix + 1
            print str(folder_alias_end_suffix)
            folder_alias_deduplicate_constructor = folder_alias_constructor + " " + str(folder_alias_end_suffix)
        folder_alias_constructor = folder_alias_deduplicate_constructor

    print("adding folder: " + folder + " with settings from template")
    # create folder entry using the selected folder, the generated alias, and values copied from template
    folderstable.insert(dict(foldersname=folder, copy_to_directory=defaults['copy_to_directory'],
                             is_active=defaults['is_active'],
                             alias=folder_alias_constructor,
                             process_backend_copy=defaults['process_backend_copy'],
                             process_backend_ftp=defaults['process_backend_ftp'],
                             process_backend_email=defaults['process_backend_email'],
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
                             ftp_port=defaults['ftp_port'],
                             email_subject_line=defaults['email_subject_line']))
    print("done")


def select_folder():
    global folder
    global column_entry_value
    folder = askdirectory()
    proposed_folder = folderstable.find_one(foldersname=folder)
    if proposed_folder is None:
        if folder != '':  # check to see if selected folder has a path
            doing_stuff_overlay.make_overlay(root, "Adding Folder...")
            column_entry_value = folder
            add_folder_entry(folder)
            doing_stuff_overlay.destroy_overlay()
            userslistframe.destroy()  # destroy lists on right
            make_users_list()  # recreate list
    else:
        #  offer to edit the folder if it is already known
        if askokcancel("Query:", "Folder already known, would you like to edit?"):
            EditDialog(root, proposed_folder)


def batch_add_folders():
    added = 0
    skipped = 0
    containing_folder = askdirectory()
    if containing_folder != "":
        os.chdir(str(containing_folder))
        folders_list = [f for f in os.listdir('.') if os.path.isdir(f)]
        print("adding " + str(len(folders_list)) + " folders")
        if askokcancel(message="This will add " + str(len(folders_list)) + " directories, are you sure?"):
            doing_stuff_overlay.make_overlay(parent=root, overlaytext="adding folders...")
            folder_count = 0
            for folder in folders_list:
                doing_stuff_overlay.destroy_overlay()
                folder_count = folder_count + 1
                doing_stuff_overlay.make_overlay(parent=root, overlaytext="adding folders... " + str(folder_count) + " of " + str(len(folders_list)))
                folder = os.path.join(containing_folder, folder)
                proposed_folder = folderstable.find_one(foldersname=folder)
                if proposed_folder is None:
                    if folder != '':  # check to see if selected folder has a path
                        add_folder_entry(folder)
                        added = added + 1
                else:
                    print("skipping existing folder: " + folder)
                    skipped = skipped + 1
            print("done adding folders")
            doing_stuff_overlay.destroy_overlay()
            refresh_users_list()
            showinfo(message=str(added) + " folders added, " + str(skipped) + " folders skipped.")


def edit_folder_selector(folder_to_be_edited):
    # feed the editdialog class the the dict for the selected folder from the folders list buttons
    # note: would prefer to be able to do this inline, but variables appear to need to be pushed out of instanced objects
    edit_folder = folderstable.find_one(id=[folder_to_be_edited])
    EditDialog(root, edit_folder)


def make_users_list():
    global userslistframe
    global active_userslistframe
    global inactive_userslistframe
    userslistframe = Frame(root)
    active_users_list_container = Frame(userslistframe)
    inactive_users_list_container = Frame(userslistframe)
    active_userslistframe = scrollbuttons.VerticalScrolledFrame(active_users_list_container)
    inactive_userslistframe = scrollbuttons.VerticalScrolledFrame(inactive_users_list_container)
    active_users_list_label = Label(active_users_list_container, text="Active Folders")  # active users title
    inactive_users_list_label = Label(inactive_users_list_container, text="Inactive Folders")  # inactive users title
    if folderstable.count(is_active="True") == 0:
        no_active_label = Label(active_userslistframe, text="No Active Folders")
        no_active_label.pack(fill=BOTH, expand=1, padx=10)
    if folderstable.count(is_active="False") == 0:
        no_inactive_label = Label(inactive_userslistframe, text="No Inactive Folders")
        no_inactive_label.pack(fill=BOTH, expand=1, padx=10)
    # iterate over list of known folders, sorting into lists of active and inactive
    for foldersname in folderstable.all():
        if str(foldersname['is_active']) != "False":
            active_folderbuttonframe = Frame(active_userslistframe.interior)
            Button(active_folderbuttonframe, text="Delete",
                   command=lambda name=foldersname['id']: delete_folder_entry_wrapper(name)).grid(column=1, row=0, sticky=E)
            Button(active_folderbuttonframe, text="Edit: " + foldersname['alias'],
                   command=lambda name=foldersname['id']: edit_folder_selector(name)).grid(column=0, row=0, sticky=E+W)
            active_folderbuttonframe.pack(anchor='e', pady=1)
        else:
            inactive_folderbuttonframe = Frame(inactive_userslistframe.interior)
            Button(inactive_folderbuttonframe, text="Delete",
                   command=lambda name=foldersname['id']: delete_folder_entry_wrapper(name)).grid(column=1, row=0, sticky=E)
            Button(inactive_folderbuttonframe, text="Edit: " + foldersname['alias'],
                   command=lambda name=foldersname['id']: edit_folder_selector(name)).grid(column=0, row=0, sticky=E+W)
            inactive_folderbuttonframe.pack(anchor='e', pady=1)
    # pack widgets in correct order
    active_users_list_label.pack(pady=5)
    Separator(active_users_list_container, orient=HORIZONTAL).pack(fill=X)
    inactive_users_list_label.pack(pady=5)
    Separator(inactive_users_list_container, orient=HORIZONTAL).pack(fill=X)
    active_userslistframe.pack(fill=BOTH, expand=1, anchor=E, padx=3, pady=3)
    inactive_userslistframe.pack(fill=BOTH, expand=1, anchor=E, padx=3, pady=3)
    active_users_list_container.pack(side=RIGHT, fill=Y, expand=1, anchor=E)
    inactive_users_list_container.pack(side=RIGHT, fill=Y, expand=1, anchor=E)
    userslistframe.pack(side=RIGHT, fill=BOTH, expand=1)


class EditReportingDialog(dialog.Dialog):  # modal dialog for folder configuration.

    def body(self, master):

        self.resizable(width=FALSE, height=FALSE)
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
        Label(master, text="Log File Folder:").grid(row=7, sticky=E)
        Label(master, text="Enable Report Printing Fallback:").grid(row=8, sticky=E)

        self.e0 = Checkbutton(master, variable=self.enable_reporting_checkbutton, onvalue="True", offvalue="False")
        self.e1 = Entry(master, width=40)
        self.e2 = Entry(master, width=40)
        self.e3 = Entry(master, show="*", width=40)
        self.e4 = Entry(master, width=40)
        self.e5 = Entry(master, width=40)
        self.e6 = Entry(master, width=40)
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

        self.e0.grid(row=0, column=1, padx=2, pady=2, sticky=W)
        self.e1.grid(row=1, column=1, padx=2, pady=2)
        self.e2.grid(row=2, column=1, padx=2, pady=2)
        self.e3.grid(row=3, column=1, padx=2, pady=2)
        self.e4.grid(row=4, column=1, padx=2, pady=2)
        self.e5.grid(row=5, column=1, padx=2, pady=2)
        self.e6.grid(row=6, column=1, padx=2, pady=2)
        self.e7.grid(row=7, column=1, padx=2, pady=2, sticky=W)
        self.e8.grid(row=8, column=1, padx=2, pady=2, sticky=W)

        return self.e1  # initial focus

    def validate(self):

        doing_stuff_overlay.make_overlay(self, "Testing Changes...")
        error_list = []
        errors = False
        if (validate_email(str(self.e1.get()), verify=True)) is False:
            error_list.append("Invalid Email Origin Address\r\n")
            errors = True
        if (validate_email(str(self.e6.get()), verify=True)) is False:
            error_list.append("Invalid Email Destination Address\r\n")
            errors = True
        if errors is True:
            error_report = ''.join(error_list)  # combine error messages into single string
            showerror(message=error_report)  # display generated error string in error dialog
            doing_stuff_overlay.destroy_overlay()
            return False
        doing_stuff_overlay.destroy_overlay()
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

        doing_stuff_overlay.make_overlay(self, "Applying Changes...")
        foldersnameapply['enable_reporting'] = str(self.enable_reporting_checkbutton.get())
        if logs_directory_is_altered is True:
            foldersnameapply['log_directory'] = logs_directory_edit
        foldersnameapply['report_email_address'] = str(self.e1.get())
        foldersnameapply['report_email_username'] = str(self.e2.get())
        foldersnameapply['report_email_password'] = str(self.e3.get())
        foldersnameapply['report_email_smtp_server'] = str(self.e4.get())
        foldersnameapply['reporting_smtp_port'] = str(self.e5.get())
        foldersnameapply['report_email_destination'] = str(self.e6.get())

        update_reporting(foldersnameapply)
        doing_stuff_overlay.destroy_overlay()


class EditDialog(dialog.Dialog):  # modal dialog for folder configuration.

    def body(self, master):

        self.resizable(width=FALSE, height=FALSE)
        global copytodirectory
        copytodirectory = None
        global destination_directory_is_altered
        destination_directory_is_altered = False
        self.folderframe = Frame(master)
        self.prefsframe = Frame(master)
        self.ediframe = Frame(master)
        self.separatorv1 = Separator(master, orient=VERTICAL)
        self.separatorv2 = Separator(master, orient=VERTICAL)
        self.backendvariable = StringVar(master)
        self.active_checkbutton = StringVar(master)
        self.process_edi = StringVar(master)
        self.upc_var_check = StringVar(master)  # define  "UPC calculation" checkbox state variable
        self.a_rec_var_check = StringVar(master)  # define "A record checkbox state variable
        self.c_rec_var_check = StringVar(master)  # define "C record" checkbox state variable
        self.c_headers_check = StringVar(master)  # define "Column Headers" checkbox state variable
        self.ampersand_check = StringVar(master)  # define "Filter Ampersand" checkbox state variable
        self.pad_arec_check = StringVar(master)
        self.process_backend_copy_check = BooleanVar(master)
        self.process_backend_ftp_check = BooleanVar(master)
        self.process_backend_email_check = BooleanVar(master)
        Label(self.folderframe, text="Folder Settings:").grid(row=0, columnspan=2, pady=3)
        Label(self.folderframe, text="Backends:").grid(row=2, sticky=W)
        if self.foldersnameinput['foldersname'] != 'template':
            Label(self.folderframe, text="Alias:").grid(row=5, sticky=E)
        Label(self.prefsframe, text="Copy Backend Settings:").grid(row=3, columnspan=2, pady=3)
        Label(self.prefsframe, text="Copy Destination:").grid(row=4, sticky=E)
        Separator(self.prefsframe, orient=HORIZONTAL).grid(row=5, columnspan=2, sticky=E+W, pady=2)
        Label(self.prefsframe, text="Ftp Backend Settings:").grid(row=6, columnspan=2, pady=3)
        Label(self.prefsframe, text="FTP Server:").grid(row=7, sticky=E)
        Label(self.prefsframe, text="FTP Port:").grid(row=8, sticky=E)
        Label(self.prefsframe, text="FTP Folder:").grid(row=9, sticky=E)
        Label(self.prefsframe, text="FTP Username:").grid(row=10, sticky=E)
        Label(self.prefsframe, text="FTP Password:").grid(row=11, sticky=E)
        Separator(self.prefsframe, orient=HORIZONTAL).grid(row=12, columnspan=2, sticky=E+W, pady=2)
        Label(self.prefsframe, text="Email Backend Settings:").grid(row=13, columnspan=2, pady=3)
        Label(self.prefsframe, text="Recipient Address:").grid(row=14, sticky=E)
        Label(self.prefsframe, text="Sender Address:").grid(row=15, sticky=E)
        Label(self.prefsframe, text="Sender Username:").grid(row=16, sticky=E)
        Label(self.prefsframe, text="Sender Password:").grid(row=17, sticky=E)
        Label(self.prefsframe, text="Email Subject:").grid(row=18, sticky=E)
        Label(self.prefsframe, text="Sender SMTP Server:").grid(row=19, sticky=E)
        Label(self.prefsframe, text="SMTP Server Port:").grid(row=20, sticky=E)
        Label(self.ediframe, text="EDI Convert Settings:").grid(row=0, column=3, columnspan=2, pady=3)
        Label(self.ediframe, text="Process EDI?").grid(row=1, column=3, sticky=E)
        Label(self.ediframe, text="Calculate UPC Check Digit:").grid(row=2, column=3, sticky=E)
        Label(self.ediframe, text="Include " + "A " + "Records:").grid(row=3, column=3, sticky=E)
        Label(self.ediframe, text="Include " + "C " + "Records:").grid(row=4, column=3, sticky=E)
        Label(self.ediframe, text="Include Headings:").grid(row=5, column=3, sticky=E)
        Label(self.ediframe, text="Filter Ampersand:").grid(row=6, column=3, sticky=E)
        Label(self.ediframe, text="Pad " + "A " + "Records:").grid(row=7, column=3, sticky=E)
        Label(self.ediframe, text="A " + "Record Padding (6 characters):").grid(row=8, column=3, sticky=E)

        def select_copy_to_directory():
            global copytodirectory
            global destination_directory_is_altered
            copytodirectory = str(askdirectory())
            destination_directory_is_altered = True

        self.e1 = Checkbutton(self.folderframe, text="Active", variable=self.active_checkbutton, onvalue="True", offvalue="False")
        self.copy_backend_checkbutton = Checkbutton(self.folderframe, text="Copy Backend", variable=self.process_backend_copy_check, onvalue=True, offvalue=False)
        self.ftp_backend_checkbutton = Checkbutton(self.folderframe, text="FTP Backend", variable=self.process_backend_ftp_check, onvalue=True, offvalue=False)
        self.email_backend_checkbutton = Checkbutton(self.folderframe, text="Email Backend", variable=self.process_backend_email_check, onvalue=True, offvalue=False)
        if self.foldersnameinput['foldersname'] != 'template':
            Label(self.folderframe, text="Folder Alias:").grid(row=6, sticky=W)
            self.e2 = Entry(self.folderframe, width=30)
        self.e4 = Button(self.prefsframe, text="Select Folder", command=lambda: select_copy_to_directory())
        self.e5 = Entry(self.prefsframe, width=30)
        self.e6 = Entry(self.prefsframe, width=30)
        self.e7 = Entry(self.prefsframe, width=30)
        self.e8 = Entry(self.prefsframe, width=30)
        self.e9 = Entry(self.prefsframe, show="*", width=30)
        self.e10 = Entry(self.prefsframe, width=30)
        self.e11 = Entry(self.prefsframe, width=30)
        self.e12 = Entry(self.prefsframe, width=30)
        self.e13 = Entry(self.prefsframe, show="*", width=30)
        self.e14 = Entry(self.prefsframe, width=30)
        self.e15 = Entry(self.prefsframe, width=30)
        self.e16 = Entry(self.prefsframe, width=30)
        self.e17 = Checkbutton(self.ediframe, variable=self.process_edi, onvalue="True", offvalue="False")
        self.e18 = Checkbutton(self.ediframe, variable=self.upc_var_check, onvalue="True", offvalue="False")
        self.e19 = Checkbutton(self.ediframe, variable=self.a_rec_var_check, onvalue="True", offvalue="False")
        self.e20 = Checkbutton(self.ediframe, variable=self.c_rec_var_check, onvalue="True", offvalue="False")
        self.e21 = Checkbutton(self.ediframe, variable=self.c_headers_check, onvalue="True", offvalue="False")
        self.e22 = Checkbutton(self.ediframe, variable=self.ampersand_check, onvalue="True", offvalue="False")
        self.e23 = Checkbutton(self.ediframe, variable=self.pad_arec_check, onvalue="True", offvalue="False")
        self.e24 = Entry(self.ediframe, width=10)

        self.active_checkbutton.set(self.foldersnameinput['is_active'])
        if self.foldersnameinput['foldersname'] != 'template':
            self.e2.insert(0, self.foldersnameinput['alias'])
        self.process_backend_copy_check.set(self.foldersnameinput['process_backend_copy'])
        self.process_backend_ftp_check.set(self.foldersnameinput['process_backend_ftp'])
        self.process_backend_email_check.set(self.foldersnameinput['process_backend_email'])
        self.e5.insert(0, self.foldersnameinput['ftp_server'])
        self.e6.insert(0, self.foldersnameinput['ftp_port'])
        self.e7.insert(0, self.foldersnameinput['ftp_folder'])
        self.e8.insert(0, self.foldersnameinput['ftp_username'])
        self.e9.insert(0, self.foldersnameinput['ftp_password'])
        self.e10.insert(0, self.foldersnameinput['email_to'])
        self.e11.insert(0, self.foldersnameinput['email_origin_address'])
        self.e12.insert(0, self.foldersnameinput['email_origin_username'])
        self.e13.insert(0, self.foldersnameinput['email_origin_password'])
        self.e14.insert(0, self.foldersnameinput['email_subject_line'])
        self.e15.insert(0, self.foldersnameinput['email_origin_smtp_server'])
        self.e16.insert(0, self.foldersnameinput['email_smtp_port'])
        self.process_edi.set(self.foldersnameinput['process_edi'])
        self.upc_var_check.set(self.foldersnameinput['calc_upc'])
        self.a_rec_var_check.set(self.foldersnameinput['inc_arec'])
        self.c_rec_var_check.set(self.foldersnameinput['inc_crec'])
        self.c_headers_check.set(self.foldersnameinput['inc_headers'])
        self.ampersand_check.set(self.foldersnameinput['filter_ampersand'])
        self.pad_arec_check.set(self.foldersnameinput['pad_arec'])
        self.e24.insert(0, self.foldersnameinput['arec_padding'])

        self.e1.grid(row=1, column=0, columnspan=2, padx=3)
        self.copy_backend_checkbutton.grid(row=3, column=0, sticky=W)
        self.ftp_backend_checkbutton.grid(row=4, column=0, sticky=W)
        self.email_backend_checkbutton.grid(row=5, column=0, sticky=W)
        if self.foldersnameinput['foldersname'] != 'template':
            self.e2.grid(row=6, column=1)
        self.e4.grid(row=4, column=1)
        self.e5.grid(row=7, column=1)
        self.e6.grid(row=8, column=1)
        self.e7.grid(row=9, column=1)
        self.e8.grid(row=10, column=1)
        self.e9.grid(row=11, column=1)
        self.e10.grid(row=14, column=1)
        self.e11.grid(row=15, column=1)
        self.e12.grid(row=16, column=1)
        self.e13.grid(row=17, column=1)
        self.e14.grid(row=18, column=1)
        self.e15.grid(row=19, column=1)
        self.e16.grid(row=20, column=1)
        self.e17.grid(row=1, column=4, sticky=W, padx=3)
        self.e18.grid(row=2, column=4, sticky=W, padx=3)
        self.e19.grid(row=3, column=4, sticky=W, padx=3)
        self.e20.grid(row=4, column=4, sticky=W, padx=3)
        self.e21.grid(row=5, column=4, sticky=W, padx=3)
        self.e22.grid(row=6, column=4, sticky=W, padx=3)
        self.e23.grid(row=7, column=4, sticky=W, padx=3)
        self.e24.grid(row=8, column=4)
        self.folderframe.pack(side=LEFT, anchor='n')
        self.separatorv1.pack(side=LEFT, fill=Y, padx=2)
        self.prefsframe.pack(side=LEFT, anchor='n')
        self.separatorv2.pack(side=LEFT, fill=Y, padx=2)
        self.ediframe.pack(side=LEFT, anchor='n')

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
        doing_stuff_overlay.make_overlay(self, "Applying Changes...")
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
        foldersnameapply['process_backend_copy'] = self.process_backend_copy_check.get()
        foldersnameapply['process_backend_ftp'] = self.process_backend_ftp_check.get()
        foldersnameapply['process_backend_email'] = self.process_backend_email_check.get()
        foldersnameapply['ftp_server'] = str(self.e5.get())
        foldersnameapply['ftp_port'] = int(self.e6.get())
        foldersnameapply['ftp_folder'] = str(self.e7.get())
        foldersnameapply['ftp_username'] = str(self.e8.get())
        foldersnameapply['ftp_password'] = str(self.e9.get())
        foldersnameapply['email_to'] = str(self.e10.get())
        foldersnameapply['email_origin_address'] = str(self.e11.get())
        foldersnameapply['email_origin_username'] = str(self.e12.get())
        foldersnameapply['email_origin_password'] = str(self.e13.get())
        foldersnameapply['email_subject_line'] = str(self.e14.get())
        foldersnameapply['email_origin_smtp_server'] = str(self.e15.get())
        foldersnameapply['email_smtp_port'] = int(self.e16.get())
        foldersnameapply['process_edi'] = str(self.process_edi.get())
        foldersnameapply['calc_upc'] = str(self.upc_var_check.get())
        foldersnameapply['inc_arec'] = str(self.a_rec_var_check.get())
        foldersnameapply['inc_crec'] = str(self.c_rec_var_check.get())
        foldersnameapply['inc_headers'] = str(self.c_headers_check.get())
        foldersnameapply['filter_ampersand'] = str(self.ampersand_check.get())
        foldersnameapply['pad_arec'] = str(self.pad_arec_check.get())
        foldersnameapply['arec_padding'] = str(self.e24.get())

        if self.foldersnameinput['foldersname'] != 'template':
            update_folder_alias(foldersnameapply)
        else:
            update_reporting(foldersnameapply)
        doing_stuff_overlay.destroy_overlay()

    def validate(self):

        error_string_constructor_list = []
        errors = False

        doing_stuff_overlay.make_overlay(self, "Testing Changes...")
        if self.process_backend_ftp_check.get() is True:
            try:
                temp_smtp_port_check = int(self.e6.get())
            except Exception:
                error_string_constructor_list.append("FTP Port Field Needs To Be A Number\r\n")
                errors = True

        if self.process_backend_email_check.get() is True:
            if (validate_email(str(self.e11.get()), verify=True)) is False:
                error_string_constructor_list.append("Invalid Email Origin Address\r\n")
                errors = True

            if (validate_email(str(self.e10.get()), verify=True)) is False:
                error_string_constructor_list.append("Invalid Email Destination Address\r\n")
                errors = True

            try:
                temp_smtp_port_check = int(self.e16.get())
            except Exception:
                error_string_constructor_list.append("SMTP Port Field Needs To Be A Number\r\n")
                errors = True


        if len(str(self.e24.get())) is not 6 and str(self.pad_arec_check.get()) == "True":
            error_string_constructor_list.append('"A" Record Padding Needs To Be Six Characters\r\n')
            errors = True

        if self.foldersnameinput['foldersname'] != 'template':
            if str(self.e2.get()) != self.foldersnameinput['alias']:
                proposed_folder = folderstable.find_one(alias=str(self.e2.get()))
                if proposed_folder is not None:
                    error_string_constructor_list.append("Folder Alias Already In Use\r\n")
                    errors = True

            if len(self.e2.get()) > 50:
                error_string_constructor_list.append("Alias Too Long\r\n")
                errors = True
        if errors is True:
            doing_stuff_overlay.destroy_overlay()
            error_string = ''.join(error_string_constructor_list)  # combine error messages into single string
            showerror(message=error_string)  # display generated error in dialog box
            return False

        doing_stuff_overlay.destroy_overlay()
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
    obe_queue.delete(folder_id=folder_to_be_removed)
    emails_table.delete(folder_id=folder_to_be_removed)


def delete_folder_entry_wrapper(folder_to_be_removed):
    delete_folder_entry(folder_to_be_removed)
    refresh_users_list()


def graphical_process_directories(folderstable_process):
    if folderstable_process.count(is_active="True") > 0:
        doing_stuff_overlay.make_overlay(parent=root, overlaytext="processing folders...")
        process_directories(folderstable_process)
        refresh_users_list()
        doing_stuff_overlay.destroy_overlay()
    else:
        showerror("Error", "No Active Folders")


def set_defaults_popup():
    defaults = oversight_and_defaults.find_one(id=1)
    EditDialog(root, defaults)


def process_directories(folderstable_process):
    original_folder = os.getcwd()
    global emails_table
    log_folder_creation_error = False
    start_time = str(datetime.datetime.now())
    reporting = oversight_and_defaults.find_one(id=1)
    run_log_name_constructor = "Run Log " + str(time.ctime()).replace(":", "-") + ".txt"
    # check for configured logs directory, and create it if necessary
    if not os.path.isdir(logs_directory['logs_directory']):
        try:
            os.mkdir(logs_directory['logs_directory'])
        except IOError:
            log_folder_creation_error = True
    if check_logs_directory() is False or log_folder_creation_error is True:
        if args.automatic is False:
            # offer to make new log directory
            while check_logs_directory() is False:  # don't let user out unless they pick a writable folder, or cancel
                if askokcancel("Error", "Can't write to log directory,\r\n would you like to change reporting settings?"):
                    EditReportingDialog(root, reporting_options)
                else:
                    # the logs must flow. aka, stop here if user declines selecting a new writable log folder
                    showerror(message="Can't write to log directory, exiting")
                    raise SystemExit
        else:
            try:
                # can't prompt for new logs directory, can only complain in a critical log and quit
                print("can't write into logs directory. in automatic mode, so no prompt. this error will be stored in critical log")
                critical_log = open("critical_error.log", 'a')
                critical_log.write(str(datetime.datetime.now()) + "can't write into logs directory. in automatic mode, so no prompt\r\n")
                critical_log.close()
                raise SystemExit
            except IOError:
                # can't complain in a critical log, so ill complain in standard output and quit
                print("Can't write critical error log, aborting")
                raise SystemExit
    run_log_path = reporting['logs_directory']
    run_log_path = str(run_log_path)  # convert possible unicode path to standard python string to fix weird path bugs
    run_log_fullpath = os.path.join(run_log_path, run_log_name_constructor)
    run_log = open(run_log_fullpath, 'w')
    run_log.write("Batch File Sender Version " + version + "\r\n")
    run_log.write("starting run at " + time.ctime() + "\r\n")
    # call dispatch module to process active folders
    try:
        dispatch.process(folderstable_process, run_log, emails_table, reporting['logs_directory'], reporting, obe_queue, root, args, version)
        os.chdir(original_folder)
    except Exception, error:
        os.chdir(original_folder)
        # if processing folders runs into a serious error, report and log
        print("Run failed, check your configuration \r\nError from dispatch module is: \r\n" + str(error) + "\r\n")
        run_log.write(
            "Run failed, check your configuration \r\nError from dispatch module is: \r\n" + str(error) + "\r\n")
    run_log.close()
    if reporting['enable_reporting'] == "True":
        emails_table.insert(dict(log=run_log_fullpath, folder_alias=run_log_name_constructor))
        try:
            sent_emails_removal_queue.delete()
            total_size = 0
            skipped_files = 0
            email_errors = cStringIO.StringIO()
            total_emails = emails_table.count()
            emails_count = 0
            batch_number = 1
            for log in emails_table.all():
                emails_count = emails_count + 1
                if os.path.isfile(log['log']):
                    # iterate over emails to send queue, breaking it into 9mb chunks if necessary
                    total_size += total_size + os.path.getsize(log['log'])  # add size of current file to total
                    emails_table_batch.insert(log)
                    if total_size > 9000000:  # if the total size is more than 9mb, then send that set and reset the total
                        batch_log_sender.do(reporting, emails_table_batch, sent_emails_removal_queue, start_time, args, root, batch_number, emails_count, total_emails)
                        emails_table_batch.delete()  # clear batch
                        total_size = 0
                        batch_number = batch_number + 1
                else:
                    email_errors.write("\r\n" + log['log'] + " missing, skipping")
                    email_errors.write("\r\n file was expected to be at " + log['log'] + " on the sending computer")
                    skipped_files = skipped_files + 1
                    sent_emails_removal_queue.insert(log)
            if emails_table_batch.count() > 0:
                # send the remainder of emails
                batch_log_sender.do(reporting, emails_table_batch, sent_emails_removal_queue, start_time, args, root, batch_number, emails_count, total_emails)
                emails_table_batch.delete()  # clear batch
            for line in sent_emails_removal_queue.all():
                emails_table.delete(log=str(line['log']))
            sent_emails_removal_queue.delete()
            if skipped_files > 0:
                batch_number = batch_number + 1
                emails_count = emails_count + 1
                email_errors.write("\r\n\r\n" + str(skipped_files) + " emails skipped")
                email_errors_log_name_constructor = "Email Errors Log " + str(time.ctime()).replace(":", "-") + ".txt"
                email_errors_log_fullpath = os.path.join(run_log_path, email_errors_log_name_constructor)
                reporting_emails_errors = open(email_errors_log_fullpath, 'w')
                reporting_emails_errors.write(email_errors.getvalue())
                reporting_emails_errors.close()
                emails_table_batch.insert(dict(log=email_errors_log_fullpath, folder_alias=email_errors_log_name_constructor))
                try:
                    batch_log_sender.do(reporting, emails_table_batch, sent_emails_removal_queue, start_time, args, root, batch_number, emails_count, total_emails)
                    emails_table_batch.delete()
                except Exception:
                    doing_stuff_overlay.destroy_overlay()
                    emails_table_batch.delete()
        except Exception, error:
            emails_table_batch.delete()
            run_log = open(run_log_fullpath, 'a')
            if reporting['report_printing_fallback'] == "True":
                print("Emailing report log failed with: " + str(error) + ", printing file\r\n")
                run_log.write("Emailing report log failed with: " + str(error) + ", printing file\r\n")
            else:
                print("Emailing report log failed with: " + str(error) + ", printing disabled, stopping\r\n")
                run_log.write("Emailing report log failed with: " + str(error) + ", printing disabled, stopping\r\n")
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


def silent_process_directories(folderstable):
    if folderstable.count(is_active="True") > 0:
        print "batch processing configured directories"
        try:
            process_directories(folderstable)
        except Exception, error:
            print(str(error))
            critical_log = open("critical_error.log", 'a')
            critical_log.write(str(error) + "\r\n")
            critical_log.close()
    else:
        print("Error, No Active Folders")
    raise SystemExit


def remove_inactive_folders():
    users_refresh = False
    if folderstable.count(is_active="False") > 0:
        users_refresh = True
    folders_total = folderstable.count(is_active="False")
    folders_count = 0
    for folder in folderstable.find(is_active="False"):
        folders_count = folders_count + 1
        doing_stuff_overlay.make_overlay(maintenance_popup, "removing " + str(folders_count) + " of " + str(folders_total))
        delete_folder_entry(folder['id'])
        doing_stuff_overlay.destroy_overlay()
    if users_refresh:
        refresh_users_list()


def move_active_to_obe():
    starting_folder = os.getcwd()
    folder_total = folderstable.count(is_active="True")
    folder_count = 0
    doing_stuff_overlay.make_overlay(maintenance_popup, "adding files to obe queue...")
    for parameters_dict in folderstable.find(is_active="True"):
        file_total = 0
        file_count = 0
        folder_count = folder_count + 1
        doing_stuff_overlay.destroy_overlay()
        doing_stuff_overlay.make_overlay(parent=maintenance_popup, overlaytext="adding files to obe queue..." + " folder " + str(folder_count) + " of " + str(folder_total) + " file " + str(file_count) + " of " + str(file_total))
        os.chdir(parameters_dict['foldersname'])
        files = [f for f in os.listdir('.') if os.path.isfile(f)]  # create list of all files in directory
        file_total = len(files)
        for filename in files:
            file_count = file_count + 1
            doing_stuff_overlay.destroy_overlay()
            doing_stuff_overlay.make_overlay(parent=maintenance_popup, overlaytext="adding files to obe queue..." + " folder " + str(folder_count) + " of " + str(folder_total) + " file " + str(file_count) + " of " + str(file_total))
            if obe_queue.find_one(file=str(os.path.abspath(filename))) is None:
                obe_queue.insert(dict(file=str(os.path.abspath(filename)), destination=str(os.path.join(parameters_dict['foldersname'], "obe")), folder_id=parameters_dict['id']))
    doing_stuff_overlay.destroy_overlay()
    os.chdir(starting_folder)


def process_obe_queue():
    error_counter = 0
    processed_counter = 0
    if obe_queue.count() > 0:
        doing_stuff_overlay.make_overlay(maintenance_popup, "processing obe queue...")
        file_count_total = obe_queue.count()
        file_count = 0
        for files in obe_queue.all():
            try:
                file_count = file_count + 1
                doing_stuff_overlay.destroy_overlay()
                doing_stuff_overlay.make_overlay(parent=maintenance_popup, overlaytext="moving files to obe folders...\n\n" + str(file_count) + " of " + str(file_count_total))
                print("moving " + files['file'] + " to obe directory")
                if os.path.isfile(files['file']):
                    if os.path.exists(files['destination']) is False:
                        print("obe folder missing, making one")
                        os.mkdir(files['destination'])
                    if os.path.isfile(os.path.join(files['destination'], os.path.basename(files['file']))) is False:
                        shutil.move(files['file'], files['destination'])
                    else:
                        print("file with same name exists, adding number to end")
                        destination_file_constructor = files['file']
                        destination_file_end_suffix = 0
                        destination_file_deduplicate_constructor = destination_file_constructor
                        while os.path.isfile(os.path.join(str(files['destination']), destination_file_deduplicate_constructor)) is True:
                            destination_file_end_suffix += destination_file_end_suffix + 1
                            print str(destination_file_end_suffix)
                            destination_file_deduplicate_constructor = destination_file_constructor + " duplicate " + str(destination_file_end_suffix)
                        destination_file_constructor = destination_file_deduplicate_constructor
                        shutil.move(str(files['file']), os.path.join(str(files['destination']), destination_file_constructor))
                    processed_counter = processed_counter + 1
                else:
                    obe_queue.delete(file=str(files['file']))
                    error_counter = error_counter + 1
            except IOError:
                error_counter = error_counter + 1
        doing_stuff_overlay.destroy_overlay()
        showinfo(message=str(processed_counter) + " files moved\r\n" + str(error_counter) + " move errors")


def set_all_inactive():
    total = folderstable.count(is_active="True")
    count = 0
    for folder in folderstable.find(is_active="True"):
        count = count + 1
        doing_stuff_overlay.make_overlay(maintenance_popup, "processing " + str(count) + " of " + str(total))
        folder['is_active'] = "False"
        folderstable.update(folder, ['id'])
        doing_stuff_overlay.destroy_overlay()
    if total > 0:
        refresh_users_list()


def set_all_active():
    total = folderstable.count(is_active="False")
    count = 0
    for folder in folderstable.find(is_active="False"):
        count = count + 1
        doing_stuff_overlay.make_overlay(maintenance_popup, "processing " + str(count) + " of " + str(total))
        folder['is_active'] = "True"
        folderstable.update(folder, ['id'])
        doing_stuff_overlay.destroy_overlay()
    if total > 0:
        refresh_users_list()


def maintenance_functions_popup():
    if askokcancel(message="Maintenance window is for advanced users only, potential for data loss if incorrectly used. Are you sure you want to continue?"):
        global maintenance_popup
        maintenance_popup = Toplevel()
        maintenance_popup.title("Maintenance Functions")
        maintenance_popup.transient(root)
        maintenance_popup.geometry("+%d+%d" % (root.winfo_rootx()+50, root.winfo_rooty()+50))
        maintenance_popup.grab_set()
        maintenance_popup.focus_set()
        maintenance_popup.resizable(width=FALSE, height=FALSE)
        maintenance_popup_button_frame = Frame(maintenance_popup)
        maintenance_popup_warning_label = Label(maintenance_popup, text="WARNING:\nFOR\nADVANCED\nUSERS\nONLY!")
        set_all_active_button = Button(maintenance_popup_button_frame, text="move all to active", command=set_all_active)
        set_all_inactive_button = Button(maintenance_popup_button_frame, text="move all to inactive", command=set_all_inactive)
        clear_emails_queue = Button(maintenance_popup_button_frame, text="clear queued emails", command=emails_table.delete)
        clear_obe_queue = Button(maintenance_popup_button_frame, text="clear obe queue", command=obe_queue.delete)
        move_active_to_obe_button = Button(maintenance_popup_button_frame, text="Move Active to obe", command=move_active_to_obe)
        process_obe_queue_button = Button(maintenance_popup_button_frame, text="Process obe queue", command=process_obe_queue)
        remove_all_inactive = Button(maintenance_popup_button_frame, text="Remove all inactive configurations", command=remove_inactive_folders)
        set_all_active_button.pack(side=TOP, fill=X, padx=2, pady=2)
        set_all_inactive_button.pack(side=TOP, fill=X, padx=2, pady=2)
        clear_emails_queue.pack(side=TOP, fill=X, padx=2, pady=2)
        clear_obe_queue.pack(side=TOP, fill=X, padx=2, pady=2)
        move_active_to_obe_button.pack(side=TOP, fill=X, padx=2, pady=2)
        process_obe_queue_button.pack(side=TOP, fill=X, padx=2, pady=2)
        remove_all_inactive.pack(side=TOP, fill=X, padx=2, pady=2)
        maintenance_popup_button_frame.pack(side=LEFT)
        maintenance_popup_warning_label.pack(side=RIGHT, padx=20)


launch_options.add_argument('-a', '--automatic', action='store_true')
args = launch_options.parse_args()
if args.automatic:
    silent_process_directories(folderstable)

open_folder_button = Button(optionsframe, text="Add Directory", command=select_folder)
open_folder_button.pack(side=TOP, fill=X, pady=2, padx=2)
open_multiple_folder_button = Button(optionsframe, text="Batch Add Directories", command=batch_add_folders)
open_multiple_folder_button.pack(side=TOP, fill=X, pady=2, padx=2)
default_settings = Button(optionsframe, text="Set Defaults", command=set_defaults_popup)
default_settings.pack(side=TOP, fill=X, pady=2, padx=2)
reporting_options = oversight_and_defaults.find_one(id=1)
edit_reporting = Button(optionsframe, text="Edit Reporting",
                        command=lambda: EditReportingDialog(root, reporting_options))
edit_reporting.pack(side=TOP, fill=X, pady=2, padx=2)
process_folder_button = Button(optionsframe, text="Process Folders", command=lambda: graphical_process_directories(folderstable))
process_folder_button.pack(side=BOTTOM, fill=X, pady=2, padx=2)
Separator(optionsframe, orient=HORIZONTAL).pack(fill='x', side=BOTTOM)
maintenance_button = Button(optionsframe, text="Maintenance", command=maintenance_functions_popup)
maintenance_button.pack(side=TOP, fill=X, pady=2, padx=2)
optionsframe.pack(side=LEFT, anchor='n', fill=Y)
optionsframe_divider = Separator(root, orient=VERTICAL)
optionsframe_divider.pack(side=LEFT, fill=Y)
# set window minimum size to prevent user making it ugly
root.update()  # update window geometry
# don't allow window to be resized smaller than current dimensions
root.minsize(root.winfo_width(), root.winfo_height())
root.resizable(width=FALSE, height=TRUE)

make_users_list()

root.mainloop()
