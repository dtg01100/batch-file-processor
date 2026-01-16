#!/usr/bin/env python3
"""
Test script for legacy database import functionality
"""

import sqlite3
import json

def create_sample_legacy_db(db_path):
    """Create a sample legacy database with test data"""
    conn = sqlite3.connect(db_path)
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
    
    # Insert sample data
    sample_folder = {
        "folder_name": "/home/user/edi_inbox",
        "alias": "EDI Processing Pipeline",
        "folder_is_active": "True",
        "connection_type": "local",
        "connection_params": json.dumps({"path": "/home/user/edi_inbox"}),
        "schedule": "*/30 * * * *",
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
        "copy_to_directory": "/home/user/csv_output",
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
    
    placeholders = ", ".join(["?" for _ in sample_folder])
    columns = ", ".join(sample_folder.keys())
    sql = f"INSERT INTO folders ({columns}) VALUES ({placeholders})"
    cursor.execute(sql, list(sample_folder.values()))
    
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
    print(f"Sample legacy database created: {db_path}")

if __name__ == "__main__":
    print("Creating sample legacy database for testing...")
    create_sample_legacy_db("/tmp/test_legacy_folders.db")
    print("Sample database created at /tmp/test_legacy_folders.db")
    print("You can now test the import functionality through the web interface.")

