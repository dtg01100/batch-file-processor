"""EditSettingsDialog for editing application-wide settings.

This module provides the EditSettingsDialog class with dependency injection
for testability, extracted from main_interface.py.
"""

import os
import tkinter
import tkinter.ttk
from typing import Any, Callable, Dict, Optional

from tkinter.filedialog import askdirectory
from tkinter.messagebox import askokcancel, showerror

import pyodbc  # type: ignore

# `doingstuffoverlay` removed — provide a no-op fallback so legacy Tk modules can still import
try:
    import doingstuffoverlay
except Exception:  # pragma: no cover - fallback for headless/Qt-only builds
    class _NoopOverlay:
        def make_overlay(self, *a, **k):
            return None
        def update_overlay(self, *a, **k):
            return None
        def destroy_overlay(self, *a, **k):
            return None
    doingstuffoverlay = _NoopOverlay()

import utils
from dialog import Dialog
from interface.services.smtp_service import SMTPService, SMTPServiceProtocol
from interface.validation.email_validator import validate_email as validate_email_format


def attach_right_click_menu(entry_widget):
    """Attach a right-click context menu to an entry widget.

    Args:
        entry_widget: A tkinter Entry widget to attach the menu to

    Returns:
        The RightClickMenu instance (in case caller needs reference)
    """
    try:
        # Try to use Qt equivalent first if available
        from interface.qt.widgets.extra_widgets import RightClickMenu
        return RightClickMenu(entry_widget)
    except (ImportError, TypeError):
        # Fall back to Tk version
        try:
            from interface.qt.widgets import extra_widgets as tk_extra_widgets
            rclick_menu = tk_extra_widgets.RightClickMenu(entry_widget)
            entry_widget.bind("<3>", rclick_menu)
            return rclick_menu
        except (ImportError, AttributeError):  # pragma: no cover
            # No-op fallback if neither version is available
            return None


class EditSettingsDialog(Dialog):
    """Modal dialog for editing application settings.

    This dialog handles email configuration, AS400 database settings,
    reporting options, and backup settings.

    Dependencies are injected for testability:
    - settings_provider: Callable to retrieve settings dict
    - oversight_provider: Callable to retrieve oversight/defaults dict
    - update_settings: Callable to persist settings changes
    - update_oversight: Callable to persist oversight changes
    - on_apply: Callback after successful apply
    - refresh_callback: Callback to refresh UI after changes
    - count_email_backends: Callable to count folders with email backend
    - count_disabled_folders: Callable to count folders that would be disabled
    - disable_email_backends: Callable to disable email backends
    - disable_folders_without_backends: Callable to disable folders
    """

    def __init__(
        self,
        parent,
        foldersnameinput: Dict[str, Any],
        title: Optional[str] = None,
        settings_provider: Optional[Callable[[], Dict[str, Any]]] = None,
        oversight_provider: Optional[Callable[[], Dict[str, Any]]] = None,
        update_settings: Optional[Callable[[Dict[str, Any]], None]] = None,
        update_oversight: Optional[Callable[[Dict[str, Any]], None]] = None,
        on_apply: Optional[Callable[[Dict[str, Any]], None]] = None,
        refresh_callback: Optional[Callable[[], None]] = None,
        count_email_backends: Optional[Callable[[], int]] = None,
        count_disabled_folders: Optional[Callable[[], int]] = None,
        disable_email_backends: Optional[Callable[[], None]] = None,
        disable_folders_without_backends: Optional[Callable[[], None]] = None,
        root: Optional[tkinter.Tk] = None,
        smtp_service: Optional[SMTPServiceProtocol] = None,
    ):
        """Initialize EditSettingsDialog with dependencies.

        Args:
            parent: Parent window
            foldersnameinput: Folder configuration dictionary
            title: Dialog title
            settings_provider: Callable to get settings dict
            oversight_provider: Callable to get oversight/defaults dict
            update_settings: Callable to persist settings
            update_oversight: Callable to persist oversight changes
            on_apply: Callback after successful apply (receives foldersnameinput)
            refresh_callback: Callback to refresh UI after changes
            count_email_backends: Callable to count folders with email backend enabled
            count_disabled_folders: Callable to count folders that would be disabled
            disable_email_backends: Callable to disable all email backends
            disable_folders_without_backends: Callable to disable folders without backends
            root: Root window for overlay display
            smtp_service: SMTP connection testing service
        """
        self._settings_provider = settings_provider
        self._oversight_provider = oversight_provider
        self._update_settings = update_settings
        self._update_oversight = update_oversight
        self._on_apply = on_apply
        self._refresh_callback = refresh_callback
        self._count_email_backends = count_email_backends
        self._count_disabled_folders = count_disabled_folders
        self._disable_email_backends = disable_email_backends
        self._disable_folders_without_backends = disable_folders_without_backends
        self._root_window = root
        self._smtp_service = smtp_service or SMTPService()

        # Initialize base dialog
        super().__init__(parent, foldersnameinput, title)

    def _get_settings(self) -> Dict[str, Any]:
        """Get settings from provider or use default."""
        if self._settings_provider:
            return self._settings_provider()
        return {}

    def body(self, master):
        """Build the dialog body."""
        self.settings = self._get_settings()
        self.resizable(width=tkinter.FALSE, height=tkinter.FALSE)
        self.logs_directory = self.foldersnameinput.get("logs_directory", "")
        self.title("Edit Settings")
        self.enable_email_checkbutton_variable = tkinter.BooleanVar(master)
        self.enable_interval_backup_variable = tkinter.BooleanVar(master)
        self.enable_reporting_checkbutton_variable = tkinter.StringVar(master)
        self.enable_report_printing_checkbutton_variable = tkinter.StringVar(master)
        self.report_edi_validator_warnings_checkbutton_variable = (
            tkinter.BooleanVar(master)
        )
        self.odbc_drivers_var = tkinter.StringVar(master)

        as400_db_connection_frame = tkinter.ttk.Frame(master=master)
        report_sending_options_frame = tkinter.ttk.Frame(master)
        email_options_frame = tkinter.ttk.Frame(master)
        interval_backups_frame = tkinter.ttk.Frame(master)

        # Label(master, text='Test').grid(row=0, column=0)
        as400_db_connection_frame.grid(
            row=0, column=0, sticky=(tkinter.W, tkinter.E), columnspan=2
        )

        tkinter.ttk.Label(as400_db_connection_frame, text="ODBC Driver:").grid(
            row=1, column=0, sticky=tkinter.E
        )
        tkinter.ttk.Label(as400_db_connection_frame, text="AS400 Address:").grid(
            row=2, column=0, sticky=tkinter.E
        )
        tkinter.ttk.Label(as400_db_connection_frame, text="AS400 Username:").grid(
            row=3, column=0, sticky=tkinter.E
        )
        tkinter.ttk.Label(as400_db_connection_frame, text="AS400 Password:").grid(
            row=4, column=0, sticky=tkinter.E
        )

        tkinter.ttk.Label(email_options_frame, text="Email Address:").grid(
            row=1, sticky=tkinter.E
        )
        tkinter.ttk.Label(email_options_frame, text="Email Username:").grid(
            row=2, sticky=tkinter.E
        )
        tkinter.ttk.Label(email_options_frame, text="Email Password:").grid(
            row=3, sticky=tkinter.E
        )
        tkinter.ttk.Label(email_options_frame, text="Email SMTP Server:").grid(
            row=4, sticky=tkinter.E
        )
        tkinter.ttk.Label(email_options_frame, text="Email SMTP Port").grid(
            row=5, sticky=tkinter.E
        )
        tkinter.ttk.Label(
            report_sending_options_frame, text="Email Destination:"
        ).grid(row=7, sticky=tkinter.E)

        def reporting_options_fields_state_set():
            if utils.normalize_bool(self.enable_reporting_checkbutton_variable.get()):
                state = tkinter.NORMAL
            else:
                state = tkinter.DISABLED
            for child in report_sending_options_frame.winfo_children():
                child.configure(state=state)

        def email_options_fields_state_set():
            if self.enable_email_checkbutton_variable.get() is False:
                self.enable_reporting_checkbutton_variable.set("False")
                state = tkinter.DISABLED
            else:
                state = tkinter.NORMAL
            for child in email_options_frame.winfo_children():
                child.configure(state=state)
            reporting_options_fields_state_set()
            self.run_reporting_checkbutton.configure(state=state)

        def interval_backup_options_set():
            if self.enable_interval_backup_variable.get():
                self.interval_backup_spinbox.configure(state=tkinter.NORMAL)
                self.interval_backup_interval_label.configure(state=tkinter.NORMAL)
            else:
                self.interval_backup_spinbox.configure(state=tkinter.DISABLED)
                self.interval_backup_interval_label.configure(
                    state=tkinter.DISABLED
                )

        self.enable_email_checkbutton = tkinter.ttk.Checkbutton(
            master,
            variable=self.enable_email_checkbutton_variable,
            onvalue=True,
            offvalue=False,
            command=email_options_fields_state_set,
            text="Enable Email",
        )
        self.run_reporting_checkbutton = tkinter.ttk.Checkbutton(
            master,
            variable=self.enable_reporting_checkbutton_variable,
            onvalue="True",
            offvalue="False",
            command=reporting_options_fields_state_set,
            text="Enable Report Sending",
        )
        self.report_edi_validator_warnings_checkbutton = tkinter.ttk.Checkbutton(
            master,
            variable=self.report_edi_validator_warnings_checkbutton_variable,
            onvalue=True,
            offvalue=False,
            text="Report EDI Validator Warnings",
        )
        self.enable_interval_backup_checkbutton = tkinter.ttk.Checkbutton(
            interval_backups_frame,
            variable=self.enable_interval_backup_variable,
            onvalue=True,
            offvalue=False,
            command=interval_backup_options_set,
            text="Enable interval backup",
        )
        self.interval_backup_interval_label = tkinter.ttk.Label(
            interval_backups_frame, text="Backup interval: "
        )
        self.interval_backup_spinbox = tkinter.ttk.Spinbox(
            interval_backups_frame, from_=1, to=5000, width=4, justify=tkinter.RIGHT
        )
        self.odbc_driver_selector_menu = tkinter.ttk.OptionMenu(
            as400_db_connection_frame,
            self.odbc_drivers_var,
            self.settings.get("odbc_driver", ""),
            *[i for i in pyodbc.drivers()],
        )

        self.as400_address_field = tkinter.ttk.Entry(
            as400_db_connection_frame, width=40
        )
        self.as400_username_field = tkinter.ttk.Entry(
            as400_db_connection_frame, width=40
        )
        self.as400_password_field = tkinter.ttk.Entry(
            as400_db_connection_frame, width=40
        )
        self.email_address_field = tkinter.ttk.Entry(email_options_frame, width=40)
        self.email_username_field = tkinter.ttk.Entry(email_options_frame, width=40)
        self.email_password_field = tkinter.ttk.Entry(
            email_options_frame, show="*", width=40
        )
        self.email_smtp_server_field = tkinter.ttk.Entry(
            email_options_frame, width=40
        )
        self.smtp_port_field = tkinter.ttk.Entry(email_options_frame, width=40)
        self.report_email_destination_field = tkinter.ttk.Entry(
            report_sending_options_frame, width=40
        )
        self.log_printing_fallback_checkbutton = tkinter.ttk.Checkbutton(
            report_sending_options_frame,
            variable=self.enable_report_printing_checkbutton_variable,
            onvalue="True",
            offvalue="False",
            text="Enable Report Printing Fallback:",
        )
        attach_right_click_menu(self.as400_address_field)
        attach_right_click_menu(self.as400_username_field)
        attach_right_click_menu(self.as400_password_field)
        attach_right_click_menu(self.email_address_field)
        attach_right_click_menu(self.email_username_field)
        attach_right_click_menu(self.email_smtp_server_field)
        attach_right_click_menu(self.smtp_port_field)
        attach_right_click_menu(self.report_email_destination_field)

        self.select_log_folder_button = tkinter.ttk.Button(
            master,
            text="Select Log Folder...",
            command=lambda: select_log_directory(),
        )

        def select_log_directory():
            try:
                if os.path.exists(self.logs_directory):
                    initial_directory = self.logs_directory
                else:
                    initial_directory = os.getcwd()
            except Exception as folder_select_error:
                print(folder_select_error)
                initial_directory = os.getcwd()
            logs_directory_edit_proposed = str(
                askdirectory(parent=master, initialdir=initial_directory)
            )
            if len(logs_directory_edit_proposed) > 0:
                self.logs_directory = logs_directory_edit_proposed

        self.enable_email_checkbutton_variable.set(self.settings.get("enable_email", False))
        self.enable_reporting_checkbutton_variable.set(
            self.foldersnameinput.get("enable_reporting", "False")
        )
        self.as400_address_field.insert(0, self.settings.get("as400_address", ""))
        self.as400_username_field.insert(0, self.settings.get("as400_username", ""))
        self.as400_password_field.insert(0, self.settings.get("as400_password", ""))
        self.email_address_field.insert(0, self.settings.get("email_address", ""))
        self.email_username_field.insert(0, self.settings.get("email_username", ""))
        self.email_password_field.insert(0, self.settings.get("email_password", ""))
        self.email_smtp_server_field.insert(0, self.settings.get("email_smtp_server", ""))
        self.smtp_port_field.insert(0, self.settings.get("smtp_port", ""))
        self.report_email_destination_field.insert(
            0, self.foldersnameinput.get("report_email_destination", "")
        )
        self.enable_interval_backup_variable.set(
            self.settings.get("enable_interval_backups", False)
        )
        self.enable_report_printing_checkbutton_variable.set(
            self.foldersnameinput.get("report_printing_fallback", "False")
        )
        self.report_edi_validator_warnings_checkbutton_variable.set(
            self.foldersnameinput.get("report_edi_errors", False)
        )
        self.interval_backup_spinbox.delete(0, "end")
        self.interval_backup_spinbox.insert(
            0, self.settings.get("backup_counter_maximum", 100)
        )

        email_options_fields_state_set()
        reporting_options_fields_state_set()

        self.enable_email_checkbutton.grid(row=1, columnspan=3, sticky=tkinter.W)
        email_options_frame.grid(row=2, columnspan=3)
        report_sending_options_frame.grid(row=5, columnspan=3)
        interval_backups_frame.grid(
            row=9, column=0, columnspan=3, sticky=tkinter.W + tkinter.E
        )
        interval_backups_frame.columnconfigure(0, weight=1)
        self.run_reporting_checkbutton.grid(
            row=3, column=0, padx=2, pady=2, sticky=tkinter.W
        )
        self.report_edi_validator_warnings_checkbutton.grid(
            row=4, column=0, padx=2, pady=2, sticky=tkinter.W
        )
        self.odbc_driver_selector_menu.grid(row=1, column=1)
        self.as400_address_field.grid(row=2, column=1, padx=2, pady=2)
        self.as400_username_field.grid(row=3, column=1, padx=2, pady=2)
        self.as400_password_field.grid(row=4, column=1, padx=2, pady=2)
        self.email_address_field.grid(row=1, column=1, padx=2, pady=2)
        self.email_username_field.grid(row=2, column=1, padx=2, pady=2)
        self.email_password_field.grid(row=3, column=1, padx=2, pady=2)
        self.email_smtp_server_field.grid(row=4, column=1, padx=2, pady=2)
        self.smtp_port_field.grid(row=5, column=1, padx=2, pady=2)
        self.report_email_destination_field.grid(row=7, column=1, padx=2, pady=2)
        self.select_log_folder_button.grid(
            row=3, column=1, padx=2, pady=2, sticky=tkinter.E, rowspan=2
        )
        self.log_printing_fallback_checkbutton.grid(
            row=8, column=1, padx=2, pady=2, sticky=tkinter.W
        )
        self.enable_interval_backup_checkbutton.grid(
            row=0, column=0, sticky=tkinter.W, padx=2, pady=2
        )
        self.interval_backup_interval_label.grid(
            row=0, column=1, sticky=tkinter.E, padx=2, pady=2
        )
        self.interval_backup_interval_label.columnconfigure(0, weight=1)
        self.interval_backup_spinbox.grid(
            row=0, column=2, sticky=tkinter.E, padx=2, pady=2
        )

        return self.email_address_field  # initial focus

    def validate(self):
        """Validate the dialog input."""
        doingstuffoverlay.make_overlay(self, "Testing Changes...")
        error_list = []
        errors = False

        if self.enable_email_checkbutton_variable.get():
            if self.email_address_field.get() == "":
                error_list.append("Email Address Is A Required Field\r")
                errors = True
            else:
                if (validate_email_format(str(self.email_address_field.get()))) is False:
                    error_list.append("Invalid Email Origin Address\r")
                    errors = True

            # Only attempt SMTP connection test if server and port were provided
            smtp_server_val = str(self.email_smtp_server_field.get()).strip()
            smtp_port_val = str(self.smtp_port_field.get()).strip()
            if smtp_server_val and smtp_port_val:
                success, error_msg = self._smtp_service.test_connection(
                    smtp_server=smtp_server_val,
                    smtp_port=smtp_port_val,
                    username=str(self.email_username_field.get()),
                    password=str(self.email_password_field.get()),
                )
                if not success:
                    error_list.append(
                        "Test Login Failed With Error\r" + (error_msg or "")
                    )
                    errors = True
            else:
                # missing server/port will be caught by subsequent required-field checks
                pass

            if (
                self.email_username_field.get() == ""
                and self.email_password_field.get() != ""
            ):
                error_list.append("Email Username Required If Password Is Set\r")
                errors = True

            if (
                self.email_password_field.get() == ""
                and self.email_username_field.get() != ""
            ):
                error_list.append(
                    "Email Username Without Password Is Not Supported\r"
                )
                errors = True

            if self.email_smtp_server_field.get() == "":
                error_list.append("SMTP Server Address Is A Required Field\r")
                errors = True

            if self.smtp_port_field.get() == "":
                error_list.append("SMTP Port Is A Required Field\r")
                errors = True

        if utils.normalize_bool(self.enable_reporting_checkbutton_variable.get()):
            if self.report_email_destination_field.get() == "":
                error_list.append(
                    "Reporting Email Destination Is A Required Field\r"
                )
                errors = True
            else:
                email_recipients = str(
                    self.report_email_destination_field.get()
                ).split(", ")
                for email_recipient in email_recipients:
                    print(email_recipient)
                    if (validate_email_format(str(email_recipient))) is False:
                        error_list.append("Invalid Email Destination Address\r\n")
                        errors = True

        if self.enable_interval_backup_variable.get():
            try:
                backup_interval = int(self.interval_backup_spinbox.get())
                if backup_interval < 1 or backup_interval > 5000:
                    raise ValueError
            except ValueError:
                error_list.append(
                    "Backup Interval Needs To Be A Number Between 1 and 5000"
                )
                errors = True

        if errors is True:
            error_report = "".join(
                error_list
            )  # combine error messages into single string
            showerror(
                parent=self, message=error_report
            )  # display generated error string in error dialog
            doingstuffoverlay.destroy_overlay()
            return False
        doingstuffoverlay.destroy_overlay()

        if not self.enable_email_checkbutton_variable.get():
            # Use injected callbacks if available
            if self._count_disabled_folders and self._count_email_backends:
                number_of_disabled_email_backends = self._count_email_backends()
                number_of_disabled_folders = self._count_disabled_folders()
            else:
                number_of_disabled_email_backends = 0
                number_of_disabled_folders = 0
            
            if number_of_disabled_folders != 0:
                if not askokcancel(
                    message="This will disable the email backend in "
                    + str(number_of_disabled_email_backends)
                    + " folders.\nAs a result, "
                    + str(number_of_disabled_folders)
                    + " folders will be disabled"
                ):
                    return False
        return 1

    def ok(self, event=None):
        """Handle OK button click."""
        if not self.validate():
            self.initial_focus.focus_set()  # put focus back
            return

        self.withdraw()
        self.update_idletasks()

        self.apply(self.foldersnameinput)
        self.cancel()

    def apply(self, folders_name_apply):
        """Apply the changes."""
        root = self._root_window if self._root_window else self.parent
        doingstuffoverlay.make_overlay(root, "Applying Changes...")
        root.update()
        folders_name_apply["enable_reporting"] = str(
            self.enable_reporting_checkbutton_variable.get()
        )
        folders_name_apply["logs_directory"] = self.logs_directory
        self.settings["odbc_driver"] = self.odbc_drivers_var.get()
        self.settings["as400_username"] = self.as400_username_field.get()
        self.settings["as400_password"] = self.as400_password_field.get()
        self.settings["as400_address"] = self.as400_address_field.get()
        self.settings["enable_email"] = self.enable_email_checkbutton_variable.get()
        self.settings["email_address"] = str(self.email_address_field.get())
        self.settings["email_username"] = str(self.email_username_field.get())
        self.settings["email_password"] = str(self.email_password_field.get())
        self.settings["email_smtp_server"] = str(self.email_smtp_server_field.get())
        self.settings["smtp_port"] = str(self.smtp_port_field.get())
        self.settings["enable_interval_backups"] = (
            self.enable_interval_backup_variable.get()
        )
        self.settings["backup_counter_maximum"] = int(
            self.interval_backup_spinbox.get()
        )
        folders_name_apply["report_email_destination"] = str(
            self.report_email_destination_field.get()
        )
        folders_name_apply["report_edi_errors"] = (
            self.report_edi_validator_warnings_checkbutton_variable.get()
        )
        
        if not self.enable_email_checkbutton_variable.get():
            # Use injected callbacks if available
            if self._disable_email_backends:
                self._disable_email_backends()
            if self._disable_folders_without_backends:
                self._disable_folders_without_backends()
            folders_name_apply["folder_is_active"] = "False"
            folders_name_apply["process_backend_email"] = False

        # Persist settings using injected callbacks
        if self._update_settings:
            self._update_settings(self.settings)
        if self._update_oversight:
            self._update_oversight(folders_name_apply)
        
        # Call on_apply callback if provided
        if self._on_apply:
            self._on_apply(folders_name_apply)
        
        doingstuffoverlay.destroy_overlay()
        
        # Call refresh callback if provided
        if self._refresh_callback:
            self._refresh_callback()
