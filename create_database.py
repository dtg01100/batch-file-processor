import dataset
import sqlalchemy
import os


def do(database_version):  # create database file with some default settings
    database_connection = dataset.connect('sqlite:///folders.db')  # connect to database

    version = database_connection['version']

    version.insert(dict(version=database_version))

    oversight_and_defaults = database_connection['administrative']

    oversight_and_defaults.insert(dict(folder_is_active="False",
                                       copy_to_directory=None,
                                       email_origin_password='',
                                       email_origin_smtp_server='smtp.gmail.com',
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
                                       report_email_address='',
                                       report_email_username='',
                                       report_email_password='',
                                       report_email_smtp_server='smtp.gmail.com',
                                       report_email_destination='',
                                       process_backend_copy=False,
                                       process_backend_ftp=False,
                                       process_backend_email=False,
                                       ftp_server='',
                                       ftp_folder='/',
                                       ftp_username='',
                                       ftp_password='',
                                       email_to='',
                                       email_origin_address='',
                                       email_origin_username='',
                                       logs_directory=os.path.join(os.getcwd(), "run_logs"),
                                       edi_converter_scratch_folder=os.path.join(os.getcwd(),
                                                                                 "edi_converter_scratch_folder"),
                                       errors_folder=os.path.join(os.getcwd(), "errors"),
                                       enable_reporting="False",
                                       report_printing_fallback="False",
                                       reporting_smtp_port=587,
                                       email_smtp_port=587,
                                       ftp_port=21,
                                       email_subject_line=""))

    processed_files = database_connection['processed_files']
    processed_files.create_column('file_name', sqlalchemy.types.String)
    processed_files.create_column('file_checksum', sqlalchemy.types.String)
    processed_files.create_column('copy_destination', sqlalchemy.types.String)
    processed_files.create_column('ftp_destination', sqlalchemy.types.String)
    processed_files.create_column('email_destination', sqlalchemy.types.String)
    processed_files.create_column('resend_flag', sqlalchemy.types.Boolean)
