import dataset
import sqlalchemy
import os


def do():  # create database file with some default settings
    database_connection = dataset.connect('sqlite:///folders.db')  # connect to database
    oversight_and_defaults = database_connection['administrative']

    oversight_and_defaults.insert(dict(is_active="False",
                                       email_origin_password='', email_origin_smtp_server='smtp.gmail.com',
                                       process_edi='False', calc_upc='False', inc_arec='False', inc_crec='False',
                                       inc_headers='False', filter_ampersand='False', pad_arec='False',
                                       arec_padding='', reporting_email='', foldersname='template', alias='',
                                       report_email_address='', report_email_username='',
                                       report_email_password='', report_email_smtp_server='smtp.gmail.com',
                                       report_email_destination='', process_backend='none', ftp_server='',
                                       ftp_folder='', ftp_username='', ftp_password='', email_to='',
                                       email_origin_address='', email_origin_username='',
                                       logs_directory=os.getcwd() + "/run_logs/", enable_reporting="False",
                                       report_printing_fallback="False", reporting_smtp_port=587, email_smtp_port=587,
                                       ftp_port=21))

    obe_queue = database_connection['obe_queue']
    obe_queue.create_column('file', sqlalchemy.types.String)
    obe_queue.create_column('destination', sqlalchemy.types.String)
