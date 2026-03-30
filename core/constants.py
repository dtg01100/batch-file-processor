"""Constants for the batch file processor application."""

from datetime import datetime

# Database version - this is the single source of truth for the current
# database schema version
# Update this when adding new database migrations
CURRENT_DATABASE_VERSION = "50"

# Date boundary constants for legacy date handling
MIN_DATE = datetime(1900, 1, 1)
MAX_DATE = datetime(9999, 12, 31)
