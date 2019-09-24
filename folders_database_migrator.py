import sqlalchemy
import os


def upgrade_database(database_connection, config_folder, running_platform):
    db_version = database_connection['version']
    db_version_dict = db_version.find_one(id=1)

    if db_version_dict['version'] == "5":
        folders_table = database_connection['folders']
        folders_table.create_column('convert_to_format', sqlalchemy.String)
        convert_to_csv_list = folders_table.find(process_edi='True')
        for line in convert_to_csv_list:
            line['convert_to_format'] = "csv"
            folders_table.update(line, ['id'])
        administrative_section = database_connection['administrative']
        administrative_section.create_column('convert_to_format', sqlalchemy.String)
        administrative_section_update_dict = administrative_section.find_one(id=1)
        administrative_section_update_dict['convert_to_format'] = "csv"
        administrative_section.update(administrative_section_update_dict, ['id'])

        update_version = dict(id=1, version="6")
        db_version.update(update_version, ['id'])

    db_version_dict = db_version.find_one(id=1)

    if db_version_dict['version'] == "6":
        processed_table = database_connection['processed_files']
        processed_table.create_column('resend_flag', sqlalchemy.Boolean)
        for line in processed_table:
            line['resend_flag'] = False
            processed_table.update(line, ['id'])

        update_version = dict(id=1, version="7")
        db_version.update(update_version, ['id'])

    db_version_dict = db_version.find_one(id=1)

    if db_version_dict['version'] == "7":
        folders_table = database_connection['folders']
        administrative_section = database_connection['administrative']
        administrative_section.create_column('tweak_edi', sqlalchemy.Boolean)
        administrative_section_update_dict = administrative_section.find_one(id=1)
        administrative_section_update_dict['tweak_edi'] = False
        administrative_section.update(administrative_section_update_dict, ['id'])

        folders_table.create_column('tweak_edi', sqlalchemy.Boolean)
        for line in folders_table:
            if line['pad_a_records'] == 'False':
                line['tweak_edi'] = False
                folders_table.update(line, ['id'])
            else:
                line['tweak_edi'] = True
                folders_table.update(line, ['id'])
        update_version = dict(id=1, version="8")
        db_version.update(update_version, ['id'])

    db_version_dict = db_version.find_one(id=1)

    if db_version_dict['version'] == "8":
        administrative_section = database_connection['administrative']
        administrative_section_update_dict = dict(id=1, single_add_folder_prior=os.path.join(os.getcwd()),
                                                  batch_add_folder_prior=os.path.join(os.getcwd()),
                                                  export_processed_folder_prior=os.path.join(os.getcwd()))

        administrative_section.update(administrative_section_update_dict, ['id'])
        update_version = dict(id=1, version="9")
        db_version.update(update_version, ['id'])

    db_version_dict = db_version.find_one(id=1)

    if db_version_dict['version'] == "9":
        administrative_section = database_connection['administrative']
        administrative_section_update_dict = dict(id=1, report_edi_errors=False)
        administrative_section.update(administrative_section_update_dict, ['id'])
        update_version = dict(id=1, version="10")
        db_version.update(update_version, ['id'])

    db_version_dict = db_version.find_one(id=1)

    if db_version_dict['version'] == "10":
        folders_table = database_connection['folders']
        administrative_section = database_connection['administrative']
        administrative_section.create_column('split_edi', sqlalchemy.Boolean)
        administrative_section_update_dict = administrative_section.find_one(id=1)
        administrative_section_update_dict['split_edi'] = False
        administrative_section.update(administrative_section_update_dict, ['id'])

        folders_table.create_column('split_edi', sqlalchemy.Boolean)
        for line in folders_table.all():
            line['split_edi'] = False
            folders_table.update(line, ['id'])
        update_version = dict(id=1, version="11")
        db_version.update(update_version, ['id'])

    db_version_dict = db_version.find_one(id=1)

    if db_version_dict['version'] == "11":
        administrative_section = database_connection['administrative']
        database_connection.create_table('settings')
        settings_table = database_connection['settings']
        administrative_section_dict = administrative_section.find_one(id=1)
        if administrative_section_dict['enable_reporting'] == "True":
            email_state = True
        else:
            email_state = False

        settings_table.insert(dict(enable_email=email_state,
                                   email_address=administrative_section_dict['report_email_address'],
                                   email_username=administrative_section_dict['report_email_username'],
                                   email_password=administrative_section_dict['report_email_password'],
                                   email_smtp_server=administrative_section_dict['report_email_smtp_server'],
                                   smtp_port=administrative_section_dict['reporting_smtp_port'],
                                   backup_counter=0,
                                   backup_counter_maximum=200,
                                   enable_interval_backups=True))
        update_version = dict(id=1, version="12")
        db_version.update(update_version, ['id'])

    db_version_dict = db_version.find_one(id=1)

    if db_version_dict['version'] == "12":
        administrative_section = database_connection['administrative']
        administrative_section_update_dict = dict(
            id=1,
            logs_directory=os.path.join(config_folder, "run_logs"),
            edi_converter_scratch_folder=os.path.join(config_folder, "edi_converter_scratch_folder"),
            errors_folder=os.path.join(config_folder, "errors")
        )
        administrative_section.update(administrative_section_update_dict, ['id'])
        update_version = dict(id=1, version="13")
        db_version.update(update_version, ['id'])

    db_version_dict = db_version.find_one(id=1)

    if db_version_dict['version'] == "13":
        database_connection.query(
            'update "folders" set "convert_to_format"="", "process_edi"="False" where "convert_to_format"="insight"')
        update_version = dict(id=1, version="14", os=running_platform)
        db_version.update(update_version, ['id'])

    db_version_dict = db_version.find_one(id=1)

    if db_version_dict['version'] == "14":
        database_connection.query("alter table 'folders' add column 'force_edi_validation'")
        database_connection.query('UPDATE "folders" SET "force_edi_validation" = 0')
        database_connection.query("alter table 'administrative' add column 'force_edi_validation'")
        database_connection.query('UPDATE "administrative" SET "force_edi_validation" = 0')
        update_version = dict(id=1, version="15", os=running_platform)
        db_version.update(update_version, ['id'])

    if db_version_dict['version'] == '15':
        database_connection.query("alter table 'folders' add column 'append_a_records'")
        database_connection.query('UPDATE "folders" SET "append_a_records" = "False"')
        database_connection.query("alter table 'folders' add column 'a_record_append_text'")
        database_connection.query('UPDATE "folders" SET "a_record_append_text" = ""')
        database_connection.query("alter table 'folders' add column 'force_txt_file_ext'")
        database_connection.query('UPDATE "folders" SET "force_txt_file_ext" = "False"')
        database_connection.query("alter table 'administrative' add column 'append_a_records'")
        database_connection.query('UPDATE "administrative" SET "append_a_records" = "False"')
        database_connection.query("alter table 'administrative' add column 'a_record_append_text'")
        database_connection.query('UPDATE "administrative" SET "a_record_append_text" = ""')
        database_connection.query("alter table 'administrative' add column 'force_txt_file_ext'")
        database_connection.query('UPDATE "administrative" SET "force_txt_file_ext" = "False"')
        update_version = dict(id=1, version="16", os=running_platform)
        db_version.update(update_version, ['id'])

    if db_version_dict['version'] == '16':
        database_connection.query("alter table 'folders' add column 'invoice_date_offset'")
        database_connection.query('UPDATE "folders" SET "invoice_date_offset" = 0')
        database_connection.query("alter table 'administrative' add column 'invoice_date_offset'")
        database_connection.query('UPDATE "administrative" SET "invoice_date_offset" = 0')
        update_version = dict(id=1, version="17", os=running_platform)
        db_version.update(update_version, ['id'])
