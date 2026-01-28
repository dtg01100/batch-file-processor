"""
Styles package for PyQt6 UI styling.

This package provides QSS stylesheets and styling utilities for the application.
"""

from importlib.resources import files

# Path to theme.qss file for loading stylesheet
THEME_QSS_PATH = files('interface.styles').joinpath('theme.qss')


def load_stylesheet() -> str:
    """
    Load the application stylesheet.
    
    Returns:
        String containing the QSS stylesheet content.
    """
    try:
        return THEME_QSS_PATH.read_text()
    except Exception:
        # Return empty string if stylesheet cannot be loaded
        return ""
