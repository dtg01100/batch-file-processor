import sqlalchemy


def upgrade_database(database_connection):

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
