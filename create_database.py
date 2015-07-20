import dataset
import os


def do():
    database_connection = dataset.connect('sqlite:///folders.db')  # connect to database
    oversight_and_defaults = database_connection['administrative']

    oversight_and_defaults.insert(dict(is_active="False",
                                       email_origin_password='', email_origin_smtp_server='',
                                       process_edi='False', calc_upc='False', inc_arec='False', inc_crec='False',
                                       inc_headers='False', filter_ampersand='False', pad_arec='False',
                                       arec_padding='', reporting_email='', folder='', alias='',
                                       report_email_address='', report_email_username='',
                                       report_email_password='', report_email_smtp_server='',
                                       report_email_destination='', process_backend='none', ftp_server='',
                                       ftp_folder='', ftp_username='', ftp_password='', email_to='',
                                       email_origin_address='', email_origin_username='',
                                       logs_directory=os.getcwd() + "/run_logs/", enable_reporting="False",
                                       report_printing_fallback="False"))
