"""
Folder domain model.

Re-exports FolderConfiguration as the canonical folder domain model.
FolderConfiguration lives in interface/models/ and provides full
serialization/deserialization against the database row format.

Import via::

    from core.domain.models.folder import FolderConfiguration
"""

# FolderConfiguration is the authoritative folder domain model.
# It lives in interface/models/ because it predates this separation;
# we re-export it here so all new code can import from core.domain.
from interface.models.folder_configuration import (  # noqa: F401
    ARecordPaddingConfiguration,
    BackendSpecificConfiguration,
    BackendType,
    ConvertFormat,
    CopyConfiguration,
    CSVConfiguration,
    EDIConfiguration,
    EmailConfiguration,
    FolderConfiguration,
    FTPConfiguration,
    InvoiceDateConfiguration,
    UPCOverrideConfiguration,
)
