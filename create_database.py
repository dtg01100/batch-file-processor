import dataset
import sqlalchemy
import os


def do(database_version, database_path, config_folder, running_platform):  # create database file with default settings
    database_connection = dataset.connect('sqlite:///' + database_path)  # connect to database

    version = database_connection['version']

    version.insert(dict(version=database_version, os=running_platform))

    oversight_and_defaults = database_connection['administrative']

    oversight_and_defaults.insert(dict(folder_is_active="False",
                                       copy_to_directory=None,
                                       process_edi='False',
                                       convert_to_format='csv',
                                       calculate_upc_check_digit='False',
                                       include_a_records='False',
                                       include_c_records='False',
                                       include_headers='False',
                                       filter_ampersand='False',
                                       tweak_edi=False,
                                       pad_a_records='False',
                                       a_record_padding='',
                                       reporting_email='',
                                       folder_name='template',
                                       alias='',
                                       report_email_destination='',
                                       process_backend_copy=False,
                                       process_backend_ftp=False,
                                       process_backend_email=False,
                                       ftp_server='',
                                       ftp_folder='/',
                                       ftp_username='',
                                       ftp_password='',
                                       email_to='',
                                       logs_directory=os.path.join(config_folder, "run_logs"),
                                       edi_converter_scratch_folder=os.path.join(config_folder,
                                                                                 "edi_converter_scratch_folder"),
                                       errors_folder=os.path.join(config_folder, "errors"),
                                       enable_reporting="False",
                                       report_printing_fallback="False",
                                       ftp_port=21,
                                       email_subject_line="",
                                       single_add_folder_prior=os.path.expanduser('~'),
                                       batch_add_folder_prior=os.path.expanduser('~'),
                                       export_processed_folder_prior=os.path.expanduser('~'),
                                       report_edi_errors=False,
                                       split_edi=False,
                                       force_edi_validation=False,
                                       append_a_records='False',
                                       a_record_append_text=''
                                       ))

    settings_table = database_connection['settings']
    settings_table.insert(dict(enable_email=False,
                               email_address='',
                               email_username='',
                               email_password='',
                               email_smtp_server='smtp.gmail.com',
                               smtp_port=587,
                               backup_counter=0,
                               backup_counter_maximum=200,
                               enable_interval_backups=True))

    processed_files = database_connection['processed_files']
    processed_files.create_column('file_name', sqlalchemy.types.String)
    processed_files.create_column('file_checksum', sqlalchemy.types.String)
    processed_files.create_column('copy_destination', sqlalchemy.types.String)
    processed_files.create_column('ftp_destination', sqlalchemy.types.String)
    processed_files.create_column('email_destination', sqlalchemy.types.String)
    processed_files.create_column('resend_flag', sqlalchemy.types.Boolean)
    processed_files.create_column('folder_id', sqlalchemy.types.Integer)
