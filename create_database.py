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
                                       process_backend_ftp=False,
                                       process_backend_email=False,
                                       ftp_server='',
                                       ftp_folder='/',
                                       ftp_username='',
                                       ftp_password='',
                                       email_to='',
                                       logs_directory=os.path.join(config_folder, "run_logs"),
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
                                       a_record_append_text='',
                                       force_txt_file_ext="False",
                                       invoice_date_offset=0,
                                       retail_uom=False,
                                       include_item_numbers=False,
                                       include_item_description=False,
                                       simple_csv_sort_order="upc_number,qty_of_units,unit_cost,description,vendor_item",
                                       split_prepaid_sales_tax_crec=False,
                                       estore_store_number=0,
                                       estore_Vendor_OId=0,
                                       estore_vendor_NameVendorOID="replaceme",
                                       estore_c_record_OID="",
                                       prepend_date_files = False,
                                       rename_file = "",
                                       override_upc_bool = False,
                                       override_upc_level = 1,
                                       override_upc_category_filter = "ALL"
                                       )

    oversight_and_defaults = database_connection['administrative']
    folders_table = database_connection['folders']

    oversight_and_defaults.insert(initial_db_dict)
    folders_table.insert(initial_db_dict)
    database_connection.query('DELETE FROM "folders"')

    settings_table = database_connection['settings']
    settings_table.insert(dict(enable_email=False,
                               email_address='',
                               email_username='',
                               email_password='',
                               email_smtp_server='smtp.gmail.com',
                               smtp_port=587,
                               backup_counter=0,
                               backup_counter_maximum=200,
                               enable_interval_backups=True,
                               odbc_driver = "Select ODBC Driver...",
                               as400_address = '',
                                as400_username = '',
                                as400_password = ''))

    processed_files = database_connection['processed_files']
    processed_files.create_column('file_name', sqlalchemy.types.String)
    processed_files.create_column('file_checksum', sqlalchemy.types.String)
    processed_files.create_column('copy_destination', sqlalchemy.types.String)
    processed_files.create_column('ftp_destination', sqlalchemy.types.String)
    processed_files.create_column('email_destination', sqlalchemy.types.String)
    processed_files.create_column('resend_flag', sqlalchemy.types.Boolean)
    processed_files.create_column('folder_id', sqlalchemy.types.Integer)
