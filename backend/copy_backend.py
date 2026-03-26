"""Copy backend for local file copies.

This module copies files to local directories with
injectable file operations support for testing.
"""

from backend.file_operations import create_file_operations
from backend.protocols import FileOperationsProtocol

# this is a testing module for local file copies
# note: process_parameters is a dict from a row in the database, passed into this module


def _resolve_destination_path(
    dest_dir: str, filename: str, file_ops: FileOperationsProtocol
) -> str:
    """Resolve a copy destination while preserving the source basename.

    When the destination filename is already present, route the copy into a
    unique subdirectory derived from the source file's parent directory. This
    preserves vendor-required filenames while avoiding silent overwrites.
    """
    dest_filename = file_ops.basename(filename)
    candidate = file_ops.join(dest_dir, dest_filename)
    if not file_ops.exists(candidate):
        return candidate

    source_parent = file_ops.basename(file_ops.dirname(filename)) or "collision"
    collision_dir = file_ops.join(dest_dir, source_parent)
    collision_candidate = file_ops.join(collision_dir, dest_filename)
    collision_index = 1

    while file_ops.exists(collision_candidate):
        collision_dir = file_ops.join(dest_dir, f"{source_parent}.{collision_index}")
        collision_candidate = file_ops.join(collision_dir, dest_filename)
        collision_index += 1

    if not file_ops.exists(collision_dir):
        file_ops.makedirs(collision_dir, exist_ok=True)

    return collision_candidate


def do(
    process_parameters: dict,
    settings_dict: dict,
    filename: str,
    file_ops: FileOperationsProtocol | None = None,
) -> bool:
    """Copy a file to a local directory.

    Args:
        process_parameters: Dictionary containing:
            - copy_to_directory: Destination directory path
        settings_dict: Settings dictionary (not used by copy backend)
        filename: Local file path to copy
        file_ops: Optional injectable file operations for testing.
                 If None, uses real file operations.

    Returns:
        True if file was copied successfully

    Raises:
        IOError: If file cannot be copied after 10 retries

    """
    file_pass = False
    counter = 0

    # Use provided file operations or create real ones
    if file_ops is None:
        file_ops = create_file_operations()

    # Ensure destination directory exists
    dest_dir = process_parameters["copy_to_directory"]
    if not file_ops.exists(dest_dir):
        try:
            file_ops.makedirs(dest_dir)
        except Exception as e:
            raise IOError(f"Failed to create destination directory '{dest_dir}': {e}")

    while not file_pass:
        try:
            destination_path = _resolve_destination_path(dest_dir, filename, file_ops)
            file_ops.copy(filename, destination_path)
            file_pass = True
        except IOError:
            if counter == 10:
                raise
            counter += 1

    return file_pass


class CopyBackend:
    """Copy backend class for object-oriented usage.

    Provides an object-oriented interface to the copy backend
    with injectable file operations support.

    Attributes:
        file_ops: File operations instance (injectable for testing)

    """

    def __init__(self, file_ops: FileOperationsProtocol | None = None) -> None:
        """Initialize copy backend.

        Args:
            file_ops: Optional injectable file operations for testing.

        """
        self.file_ops = file_ops

    def copy(
        self, process_parameters: dict, settings_dict: dict, filename: str
    ) -> bool:
        """Copy a file to a local directory.

        Args:
            process_parameters: Copy parameters
            settings_dict: Settings dictionary
            filename: File to copy

        Returns:
            True if successful

        """
        return do(process_parameters, settings_dict, filename, self.file_ops)

    def send(
        self, process_parameters: dict, settings_dict: dict, filename: str
    ) -> bool:
        """Send a file via copy (local file copy).

        Args:
            process_parameters: Copy parameters
            settings_dict: Settings dictionary
            filename: File to send (copy)

        Returns:
            True if successful

        """
        return self.copy(process_parameters, settings_dict, filename)

    @staticmethod
    def create_file_ops() -> FileOperationsProtocol:
        """Create a file operations instance.

        Returns:
            File operations instance

        """
        return create_file_operations()
