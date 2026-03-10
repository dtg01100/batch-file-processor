#!/usr/bin/env python3
import os
import sys

os.chdir('/workspaces/batch-file-processor')
sys.path.insert(0, '/workspaces/batch-file-processor')

from PyQt6.QtWidgets import QApplication, QWidget

app = QApplication(sys.argv)

from interface.qt.dialogs.edit_settings_dialog import EditSettingsDialog

settings_data = {
    'as400_address': 'test.example.com',
    'as400_username': 'user',
    'as400_password': 'pass',
    'email_enabled': False,
    'email_address': 'test@example.com',
    'email_username': 'user',
    'email_password': 'pass',
    'email_smtp_server': 'smtp.example.com',
    'email_smtp_port': '587',
    'email_destination': 'dest@example.com',
    'email_use_tls': True,
    'reporting_enabled': False,
    'backup_enabled': False,
}

parent = QWidget()
dialog = EditSettingsDialog(parent, settings_data)
dialog.show()
dialog.resize(700, 576)

app.processEvents()
screen = app.primaryScreen()
pixmap = screen.grabWindow(dialog.winId())
path = '/workspaces/batch-file-processor/settings_dialog_screenshot.png'
pixmap.save(path)
print(f'Saved to {path}, exists: {os.path.exists(path)}')
