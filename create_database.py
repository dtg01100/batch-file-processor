def do(database_version, database_path, config_folder, running_platform):
    """Create or initialize the database using the centralized business_logic.db helpers.

    This function preserves the original CLI/GUI entrypoint signature used by
    the rest of the application but delegates the creation and migration logic
    to business_logic.db.init_db. It then adjusts the version/administrative
    rows so the behavior matches the previous implementation.
    """
    import os
    import sqlalchemy
    import logging
    from business_logic import db as bl_db

    # Initialize (create/open) database via centralized module
    bl_db.init_db(database_path)
    conn = bl_db.get_connection()

    # Ensure version row reflects the requested database_version and running platform
    try:
        version_table = conn["version"]
        version_table.update(dict(id=1, version=str(database_version), os=running_platform), ["id"])
    except Exception:
        # be tolerant if table/row manipulation fails
        pass

    # Update administrative defaults to reference the provided config_folder paths
    try:
        oversight_and_defaults = conn["administrative"]
        oversight_and_defaults.update(
            dict(
                id=1,
                logs_directory=os.path.join(config_folder, "run_logs"),
                errors_folder=os.path.join(config_folder, "errors"),
            ),
            ["id"],
        )
    except Exception:
        pass

    # Ensure settings table defaults exist (matching previous behavior)
    try:
        settings_table = conn["settings"]
        # Attempt to insert defaults only if settings table appears empty
        if settings_table.count() == 0:
            settings_table.insert(
                dict(
                    enable_email=False,
                    email_address="",
                    email_username="",
                    email_password="",
                    email_smtp_server="smtp.gmail.com",
                    smtp_port=587,
                    backup_counter=0,
                    backup_counter_maximum=200,
                    enable_interval_backups=True,
                    odbc_driver="Select ODBC Driver...",
                    as400_address="",
                    as400_username="",
                    as400_password="",
                )
            )
    except Exception:
        pass

    # Create indexes for better query performance (SQLite-safe)
    try:
        conn = bl_db.get_connection()
        
        # Check if we're using SQLite
        db_url = getattr(conn, 'url', '')
        is_sqlite = 'sqlite' in db_url.lower()
        
        if is_sqlite:
            # Create indexes for commonly queried columns
            indexes_to_create = [
                ("idx_processed_files_file_name", "processed_files", "file_name"),
                ("idx_processed_files_folder_id", "processed_files", "folder_id"),
                ("idx_processed_files_status", "processed_files", "status"),
                ("idx_folders_folder_name", "folders", "folder_name"),
                ("idx_folders_folder_is_active", "folders", "folder_is_active"),
                ("idx_administrative_id", "administrative", "id"),
                ("idx_settings_id", "settings", "id"),
            ]
            
            for index_name, table_name, column_name in indexes_to_create:
                try:
                    # Use IF NOT EXISTS for SQLite safety
                    conn.query(f'CREATE INDEX IF NOT EXISTS "{index_name}" ON "{table_name}" ("{column_name}")')
                except Exception as e:
                    logger = logging.getLogger("batch_file_processor")
                    logger.debug(f"Could not create index {index_name}: {e}")
                    # Continue with other indexes even if one fails
    except Exception:
        # Index creation is optional - don't fail the entire process
        pass

    # Ensure processed_files has expected columns
    try:
        processed_files = conn["processed_files"]
        processed_files.create_column("file_name", sqlalchemy.types.String)
        processed_files.create_column("file_checksum", sqlalchemy.types.String)
        processed_files.create_column("copy_destination", sqlalchemy.types.String)
        processed_files.create_column("ftp_destination", sqlalchemy.types.String)
        processed_files.create_column("email_destination", sqlalchemy.types.String)
        processed_files.create_column("resend_flag", sqlalchemy.types.Boolean)
        processed_files.create_column("folder_id", sqlalchemy.types.Integer)
    except Exception:
        pass
