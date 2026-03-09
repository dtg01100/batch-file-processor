def apply_migration(database_connection):
    """
    Migration to add plugin_config column to the folders table.
    This migration is applied when upgrading from database version 32 to 33.
    """
    try:
        # Add plugin_config column to folders table - wrap in try in case it already exists
        try:
            database_connection.query("ALTER TABLE 'folders' ADD COLUMN 'plugin_config' TEXT")
            # Set default value for existing records
            database_connection.query("UPDATE 'folders' SET plugin_config = '{}' WHERE plugin_config IS NULL")
        except RuntimeError:
            # Column may already exist, which is fine
            pass
        
        # Some schema versions also have plugin_config on administrative table
        try:
            database_connection.query("ALTER TABLE 'administrative' ADD COLUMN 'plugin_config' TEXT")
            database_connection.query("UPDATE 'administrative' SET plugin_config = '{}' WHERE plugin_config IS NULL")
        except RuntimeError:
            # Column may already exist, which is fine
            pass
        
        # Add split_edi_filter columns to folders table
        try:
            database_connection.query("ALTER TABLE 'folders' ADD COLUMN 'split_edi_filter_categories' TEXT")
            database_connection.query("UPDATE 'folders' SET split_edi_filter_categories = 'ALL' WHERE split_edi_filter_categories IS NULL")
        except RuntimeError:
            pass
            
        try:
            database_connection.query("ALTER TABLE 'folders' ADD COLUMN 'split_edi_filter_mode' TEXT")
            database_connection.query("UPDATE 'folders' SET split_edi_filter_mode = 'include' WHERE split_edi_filter_mode IS NULL")
        except RuntimeError:
            pass
            
        # Add split_edi_filter columns to administrative table
        try:
            database_connection.query("ALTER TABLE 'administrative' ADD COLUMN 'split_edi_filter_categories' TEXT")
            database_connection.query("UPDATE 'administrative' SET split_edi_filter_categories = 'ALL' WHERE split_edi_filter_categories IS NULL")
        except RuntimeError:
            pass
            
        try:
            database_connection.query("ALTER TABLE 'administrative' ADD COLUMN 'split_edi_filter_mode' TEXT")
            database_connection.query("UPDATE 'administrative' SET split_edi_filter_mode = 'include' WHERE split_edi_filter_mode IS NULL")
        except RuntimeError:
            pass
            
        return True
    except Exception as e:
        print(f"Migration failed: {e}")
        return False
