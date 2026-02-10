import os

import dataset
import sqlalchemy


def do(database_version, database_path, config_folder, running_platform):  # create database file with default settings
    database_connection = dataset.connect('sqlite:///' + database_path)  # connect to database

    version = database_connection['version']

    version.insert(dict(version=database_version, os=running_platform))

    initial_db_dict = dict(folder_is_active="False",
                                       copy_to_directory=None,
                                       process_edi='False',
                                       convert_to_format='csv',
                                       calculate_upc_check_digit='False',
                                       upc_target_length=11,
                                       upc_padding_pattern='           ',
                                       include_a_records='False',
                                       include_c_records='False',
                                       include_headers='False',
                                       filter_ampersand='False',
                                       tweak_edi=False,
                                       pad_a_records='False',
                                       a_record_padding='',
                                       a_record_padding_length = 6,
                                       invoice_date_custom_format_string = "%Y%m%d",
                                       invoice_date_custom_format = False,
                                       reporting_email='',
                                       folder_name='template',
                                       alias='',
                                       report_email_destination='',
                                       process_backend_copy=False,
                                       backend_copy_destination=None,
                                       process_edi_output=False,
                                       edi_output_folder=None,
                                       )

    settings = database_connection['settings']
    settings.insert(initial_db_dict)

    database_connection.commit()
    database_connection.close()
