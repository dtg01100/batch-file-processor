def pytest_configure(config):
    # Create all mock modules first
    tkinter_mod = types.ModuleType('tkinter')
    ttk_mod = types.ModuleType('tkinter.ttk')
    messagebox_mod = types.ModuleType('tkinter.messagebox')
    filedialog_mod = types.ModuleType('tkinter.filedialog')

    # Add attributes to ttk_mod
    for attr in ['Frame', 'Label', 'Checkbutton', 'Entry', 'OptionMenu', 'Spinbox', 'Separator', 'Button']:
        setattr(ttk_mod, attr, mock.Mock())

    # Add attributes to tkinter_mod
    for attr in ['IntVar', 'Tk', 'Toplevel', 'Listbox', 'Scrollbar', 'BooleanVar', 'StringVar']:
        setattr(tkinter_mod, attr, mock.Mock())

    # Add attributes to messagebox_mod
    for attr in ['_show', 'showerror', 'showinfo', 'showwarning', 'askokcancel', 'askyesno']:
        setattr(messagebox_mod, attr, mock.Mock())

    # Add attributes to filedialog_mod
    for attr in ['askdirectory', 'askopenfilename']:
        setattr(filedialog_mod, attr, mock.Mock())

    # Attach submodules to tkinter_mod
    setattr(tkinter_mod, 'ttk', ttk_mod)
    setattr(tkinter_mod, 'messagebox', messagebox_mod)
    setattr(tkinter_mod, 'filedialog', filedialog_mod)

    # Patch sys.modules
    sys.modules['tkinter'] = tkinter_mod
    sys.modules['tkinter.ttk'] = ttk_mod
    sys.modules['tkinter.messagebox'] = messagebox_mod
    sys.modules['tkinter.filedialog'] = filedialog_mod
    setattr(messagebox_mod, 'askokcancel', mock.Mock())
    setattr(messagebox_mod, 'askyesno', mock.Mock())
    setattr(tkinter_mod, 'messagebox', messagebox_mod)
    # Patch sys.modules
    sys.modules['tkinter'] = tkinter_mod
    sys.modules['tkinter.ttk'] = ttk_mod
    sys.modules['tkinter.messagebox'] = messagebox_mod
# test_mover_tkmock.py
"""
This file provides a pytest fixture to globally mock tkinter, tkinter.ttk, and tkinter.messagebox for all tests that import it.
This avoids root window errors and missing attribute errors in headless test environments.
"""

import sys
import types
import pytest
from unittest import mock

@pytest.fixture(autouse=True, scope="session")
def patch_tkinter_modules():
    # Create tkinter mock module
    tkinter_mod = types.ModuleType('tkinter')
    setattr(tkinter_mod, 'IntVar', mock.Mock())
    setattr(tkinter_mod, 'Tk', mock.Mock())
    # Create tkinter.ttk mock module
    ttk_mod = types.ModuleType('tkinter.ttk')
    for attr in [
        'Frame', 'Label', 'Checkbutton', 'Entry', 'OptionMenu', 'Spinbox', 'Separator', 'Button']:
        setattr(ttk_mod, attr, mock.Mock())
    # Attach ttk to tkinter
    setattr(tkinter_mod, 'ttk', ttk_mod)
    # Add Listbox, Scrollbar, BooleanVar, StringVar, IntVar to tkinter
    for attr in ['Listbox', 'Scrollbar', 'BooleanVar', 'StringVar', 'IntVar']:
        setattr(tkinter_mod, attr, mock.Mock())
    # Create tkinter.messagebox mock module
    messagebox_mod = types.ModuleType('tkinter.messagebox')
    setattr(messagebox_mod, '_show', mock.Mock())
    setattr(messagebox_mod, 'showerror', mock.Mock())
    setattr(messagebox_mod, 'showinfo', mock.Mock())
    setattr(messagebox_mod, 'showwarning', mock.Mock())
    setattr(messagebox_mod, 'askokcancel', mock.Mock())
    setattr(messagebox_mod, 'askyesno', mock.Mock())
    setattr(tkinter_mod, 'messagebox', messagebox_mod)
    # Patch sys.modules
    sys.modules['tkinter'] = tkinter_mod
    sys.modules['tkinter.ttk'] = ttk_mod
    sys.modules['tkinter.messagebox'] = messagebox_mod
    yield
    # Optionally cleanup after tests
    for mod in ['tkinter', 'tkinter.ttk', 'tkinter.messagebox']:
        if mod in sys.modules:
            del sys.modules[mod]

import sys
import types
import pytest
from unittest import mock
