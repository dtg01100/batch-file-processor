import dataset

def do():
    database_connection = dataset.connect('sqlite:///folders.db')  # connect to database
    oversight_and_defaults = database_connection['administrative']
    oversight_and_defaults.insert(dict(is_active="False",
                         process_backend='null', ftp_server='null', ftp_folder='null',
                         ftp_username='null', ftp_password='null',
                         email_to='null', email_origin_address='null', email_origin_username='null',
                         email_origin_password='null', email_origin_smtp_server='null', process_edi='False', calc_upc='False',
                         inc_arec='False', inc_crec='False', inc_headers='False', filter_ampersand='False',
                         pad_arec='False', arec_padding='null', reporting_email='null', folder='null', alias='null'))
