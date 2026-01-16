"""
Test fixtures for legacy database import functionality
Provides reusable test data and database fixtures
"""

import sqlite3
import json
import tempfile
import os
from pathlib import Path

class LegacyDatabaseFixture:
    """A fixture class to create standardized legacy database test data"""
    
    @staticmethod
    def create_minimal_db():
        """Create a minimal legacy database with basic folder configuration"""
        fd, path = tempfile.mkstemp(suffix='.db')
        os.close(fd)  # Close the file descriptor to avoid locking issues
        conn = sqlite3.connect(path)
        cursor = conn.cursor()
        
        # Create folders table
        cursor.execute("""
            CREATE TABLE folders (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                folder_name TEXT,
                alias TEXT,
                folder_is_active TEXT,
                connection_type TEXT,
                connection_params TEXT,
                schedule TEXT,
                enabled TEXT,
                process_edi TEXT,
                convert_to_format TEXT,
                tweak_edi TEXT,
                split_edi TEXT,
                force_edi_validation INTEGER,
                append_a_records TEXT,
                a_record_append_text TEXT,
                invoice_date_offset INTEGER,
                retail_uom INTEGER,
                force_each_upc INTEGER,
                include_item_numbers INTEGER,
                include_item_description INTEGER,
                process_backend_copy INTEGER,
                copy_to_directory TEXT,
                process_backend_ftp INTEGER,
                ftp_server TEXT,
                ftp_folder TEXT,
                ftp_username TEXT,
                ftp_password TEXT,
                ftp_port INTEGER,
                process_backend_email INTEGER,
                email_to TEXT,
                email_subject_line TEXT
            )
        """)
        
        # Insert minimal test data
        test_folder = {
            "folder_name": "/test/input",
            "alias": "Minimal Test Pipeline",
            "folder_is_active": "True",
            "connection_type": "local",
            "connection_params": json.dumps({"path": "/test/input"}),
            "schedule": "*/30 * * * *",
            "enabled": "True",
            "process_edi": "False",
            "convert_to_format": "",
            "tweak_edi": "False",
            "split_edi": "False",
            "force_edi_validation": 0,
            "append_a_records": "False",
            "a_record_append_text": "",
            "invoice_date_offset": 0,
            "retail_uom": 0,
            "force_each_upc": 0,
            "include_item_numbers": 0,
            "include_item_description": 0,
            "process_backend_copy": 1,
            "copy_to_directory": "/test/output",
            "process_backend_ftp": 0,
            "ftp_server": "",
            "ftp_folder": "",
            "ftp_username": "",
            "ftp_password": "",
            "ftp_port": 21,
            "process_backend_email": 0,
            "email_to": "",
            "email_subject_line": ""
        }
        
        placeholders = ", ".join(["?" for _ in test_folder])
        columns = ", ".join(test_folder.keys())
        sql = f"INSERT INTO folders ({columns}) VALUES ({placeholders})"
        cursor.execute(sql, list(test_folder.values()))
        
        # Create version table
        cursor.execute("""
            CREATE TABLE version (
                id INTEGER PRIMARY KEY,
                version TEXT,
                os TEXT
            )
        """)
        
        cursor.execute("INSERT INTO version (id, version, os) VALUES (1, '32', 'Linux')")
        
        conn.commit()
        conn.close()
        
        return path

    @staticmethod
    def create_complex_db():
        """Create a complex legacy database with multiple folders and various configurations"""
        fd, path = tempfile.mkstemp(suffix='.db')
        os.close(fd)
        conn = sqlite3.connect(path)
        cursor = conn.cursor()
        
        # Create tables
        cursor.execute("""
            CREATE TABLE folders (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                folder_name TEXT,
                alias TEXT,
                folder_is_active TEXT,
                connection_type TEXT,
                connection_params TEXT,
                schedule TEXT,
                enabled TEXT,
                process_edi TEXT,
                convert_to_format TEXT,
                tweak_edi TEXT,
                split_edi TEXT,
                force_edi_validation INTEGER,
                append_a_records TEXT,
                a_record_append_text TEXT,
                invoice_date_offset INTEGER,
                retail_uom INTEGER,
                force_each_upc INTEGER,
                include_item_numbers INTEGER,
                include_item_description INTEGER,
                process_backend_copy INTEGER,
                copy_to_directory TEXT,
                process_backend_ftp INTEGER,
                ftp_server TEXT,
                ftp_folder TEXT,
                ftp_username TEXT,
                ftp_password TEXT,
                ftp_port INTEGER,
                process_backend_email INTEGER,
                email_to TEXT,
                email_subject_line TEXT
            )
        """)
        
        # Insert multiple test folders with different configurations
        test_folders = [
            {
                "folder_name": "/edi/inbox",
                "alias": "EDI Processing Pipeline",
                "folder_is_active": "True",
                "connection_type": "local",
                "connection_params": json.dumps({"path": "/edi/inbox"}),
                "schedule": "*/15 * * * *",
                "enabled": "True",
                "process_edi": "True",
                "convert_to_format": "csv",
                "tweak_edi": "True",
                "split_edi": "True",
                "force_edi_validation": 1,
                "append_a_records": "False",
                "a_record_append_text": "",
                "invoice_date_offset": 0,
                "retail_uom": 0,
                "force_each_upc": 0,
                "include_item_numbers": 1,
                "include_item_description": 1,
                "process_backend_copy": 1,
                "copy_to_directory": "/csv/output",
                "process_backend_ftp": 0,
                "ftp_server": "",
                "ftp_folder": "",
                "ftp_username": "",
                "ftp_password": "",
                "ftp_port": 21,
                "process_backend_email": 0,
                "email_to": "",
                "email_subject_line": ""
            },
            {
                "folder_name": "/invoices/inbox",
                "alias": "Invoice Processing Pipeline",
                "folder_is_active": "True",
                "connection_type": "sftp",
                "connection_params": json.dumps({
                    "host": "sftp.example.com",
                    "username": "user",
                    "password": "password",
                    "port": 22
                }),
                "schedule": "0 8 * * *",
                "enabled": "True",
                "process_edi": "True",
                "convert_to_format": "fintech",
                "tweak_edi": "False",
                "split_edi": "False",
                "force_edi_validation": 0,
                "append_a_records": "True",
                "a_record_append_text": "APPEND_TEXT",
                "invoice_date_offset": 5,
                "retail_uom": 1,
                "force_each_upc": 1,
                "include_item_numbers": 0,
                "include_item_description": 0,
                "process_backend_copy": 0,
                "copy_to_directory": "",
                "process_backend_ftp": 1,
                "ftp_server": "ftp.example.com",
                "ftp_folder": "/upload",
                "ftp_username": "ftpuser",
                "ftp_password": "ftppass",
                "ftp_port": 21,
                "process_backend_email": 0,
                "email_to": "",
                "email_subject_line": ""
            },
            {
                "folder_name": "/reports/inbox",
                "alias": "Report Pipeline",
                "folder_is_active": "False",  # Inactive
                "connection_type": "local",
                "connection_params": json.dumps({"path": "/reports/inbox"}),
                "schedule": "0 10 * * 1",
                "enabled": "False",
                "process_edi": "False",
                "convert_to_format": "json",
                "tweak_edi": "False",
                "split_edi": "False",
                "force_edi_validation": 0,
                "append_a_records": "False",
                "a_record_append_text": "",
                "invoice_date_offset": 0,
                "retail_uom": 0,
                "force_each_upc": 0,
                "include_item_numbers": 0,
                "include_item_description": 0,
                "process_backend_copy": 0,
                "copy_to_directory": "",
                "process_backend_ftp": 0,
                "ftp_server": "",
                "ftp_folder": "",
                "ftp_username": "",
                "ftp_password": "",
                "ftp_port": 21,
                "process_backend_email": 1,
                "email_to": "admin@example.com",
                "email_subject_line": "Daily Reports"
            }
        ]
        
        for folder in test_folders:
            placeholders = ", ".join(["?" for _ in folder])
            columns = ", ".join(folder.keys())
            sql = f"INSERT INTO folders ({columns}) VALUES ({placeholders})"
            cursor.execute(sql, list(folder.values()))
        
        # Create version table
        cursor.execute("""
            CREATE TABLE version (
                id INTEGER PRIMARY KEY,
                version TEXT,
                os TEXT
            )
        """)
        
        cursor.execute("INSERT INTO version (id, version, os) VALUES (1, '32', 'Linux')")
        
        conn.commit()
        conn.close()
        
        return path

    @staticmethod
    def create_empty_db():
        """Create an empty legacy database with just the schema"""
        fd, path = tempfile.mkstemp(suffix='.db')
        os.close(fd)
        conn = sqlite3.connect(path)
        cursor = conn.cursor()
        
        # Create tables but don't insert any data
        cursor.execute("""
            CREATE TABLE folders (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                folder_name TEXT,
                alias TEXT,
                folder_is_active TEXT,
                connection_type TEXT,
                connection_params TEXT,
                schedule TEXT,
                enabled TEXT,
                process_edi TEXT,
                convert_to_format TEXT,
                tweak_edi TEXT,
                split_edi TEXT,
                force_edi_validation INTEGER,
                append_a_records TEXT,
                a_record_append_text TEXT,
                invoice_date_offset INTEGER,
                retail_uom INTEGER,
                force_each_upc INTEGER,
                include_item_numbers INTEGER,
                include_item_description INTEGER,
                process_backend_copy INTEGER,
                copy_to_directory TEXT,
                process_backend_ftp INTEGER,
                ftp_server TEXT,
                ftp_folder TEXT,
                ftp_username TEXT,
                ftp_password TEXT,
                ftp_port INTEGER,
                process_backend_email INTEGER,
                email_to TEXT,
                email_subject_line TEXT
            )
        """)
        
        # Create version table
        cursor.execute("""
            CREATE TABLE version (
                id INTEGER PRIMARY KEY,
                version TEXT,
                os TEXT
            )
        """)
        
        cursor.execute("INSERT INTO version (id, version, os) VALUES (1, '32', 'Linux')")
        
        conn.commit()
        conn.close()
        
        return path

    @staticmethod
    def create_corrupted_db():
        """Create a corrupted database file for error testing"""
        fd, path = tempfile.mkstemp(suffix='.db')
        os.close(fd)
        with open(path, 'wb') as f:
            f.write(b"This is not a valid SQLite database file")
        return path

def get_fixture(fixture_name):
    """Get a specific fixture by name"""
    fixtures = {
        'minimal': LegacyDatabaseFixture.create_minimal_db,
        'complex': LegacyDatabaseFixture.create_complex_db,
        'empty': LegacyDatabaseFixture.create_empty_db,
        'corrupted': LegacyDatabaseFixture.create_corrupted_db,
    }
    
    if fixture_name not in fixtures:
        raise ValueError(f"Unknown fixture: {fixture_name}")
    
    return fixtures[fixture_name]()

# Convenience functions for common test scenarios
def create_minimal_db():
    return LegacyDatabaseFixture.create_minimal_db()

def create_complex_db():
    return LegacyDatabaseFixture.create_complex_db()

def create_empty_db():
    return LegacyDatabaseFixture.create_empty_db()

def create_corrupted_db():
    return LegacyDatabaseFixture.create_corrupted_db()