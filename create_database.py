import os

from interface.database import sqlite_wrapper
import sqlalchemy
import schema


def do(
    database_version, database_path, config_folder, running_platform
):  # create database file with default settings
    database_connection = sqlite_wrapper.Database.connect(
        database_path
    )  # connect to database
    # Ensure core tables exist using centralized schema definitions
    schema.ensure_schema(database_connection)

    version = database_connection["version"]

    version.insert(dict(version=database_version, os=running_platform))

    initial_db_dict = dict(
        folder_is_active=0,
        copy_to_directory=None,
        process_edi=0,
        convert_to_format="csv",
        calculate_upc_check_digit=0,
        upc_target_length=11,
        upc_padding_pattern="           ",
        include_a_records=0,
        include_c_records=0,
        include_headers=0,
        filter_ampersand=0,
        tweak_edi=0,
        pad_a_records=0,
        a_record_padding="",
        a_record_padding_length=6,
        invoice_date_custom_format_string="%Y%m%d",
        invoice_date_custom_format=0,
        reporting_email="",
        folder_name="template",
        alias="",
        report_email_destination="",
        process_backend_copy=0,
        backend_copy_destination=None,
        process_edi_output=0,
        edi_output_folder=None,
    )

    settings = database_connection["settings"]
    settings.insert(initial_db_dict)

    administrative = database_connection["administrative"]
    administrative.insert(
        dict(
            id=1,
            copy_to_directory="",
            logs_directory=os.path.join(os.path.expanduser("~"), "BatchFileSenderLogs"),
            enable_reporting=0,
            report_email_destination="",
            report_edi_errors=0,
        )
    )

    database_connection.commit()
    database_connection.close()
