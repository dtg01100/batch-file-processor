"""Copy backend for local file copies.

This module copies files to local directories with
injectable file operations support for testing.
"""

from backend.backend_base import BackendBase
from backend.file_operations import create_file_operations
from backend.protocols import FileOperationsProtocol
from core.structured_logging import get_logger

logger = get_logger(__name__)


def do(
    process_parameters: dict,
    settings_dict: dict,
    filename: str,
    file_ops: FileOperationsProtocol | None = None,
    disable_retry: bool = False,
) -> bool:
    """Copy a file to a local directory.

    Args:
        process_parameters: Dictionary containing copy_to_directory
        settings_dict: Settings dictionary (not used)
        filename: Local file path to copy
        file_ops: Optional injectable file operations for testing
        disable_retry: If True, skip retry logic (for faster tests)

    Returns:
        True if file was copied successfully

    Raises:
        IOError: If file cannot be copied after 10 retries

    """
    backend = CopyBackend(file_ops=file_ops, disable_retry=disable_retry)
    return backend.copy(process_parameters, settings_dict, filename)


class CopyBackend(BackendBase):
    """Copy backend class for object-oriented usage.

    Provides an object-oriented interface to the copy backend
    with injectable file operations support.
    """

    def __init__(
        self,
        file_ops: FileOperationsProtocol | None = None,
        disable_retry: bool = False,
    ) -> None:
        """Initialize copy backend.

        Args:
            file_ops: Optional injectable file operations for testing.
            disable_retry: If True, skip retry logic (for testing)

        """
        super().__init__(disable_retry=disable_retry)
        self.file_ops = file_ops if file_ops is not None else create_file_operations()

    def _resolve_destination(self, dest_dir: str, filename: str) -> str:
        """Resolve a copy destination while preserving the source basename.

        When the destination filename is already present, route the copy into a
        unique subdirectory derived from the source file's parent directory. This
        preserves vendor-required filenames while avoiding silent overwrites.
        """
        dest_filename = self.file_ops.basename(filename)
        candidate = self.file_ops.join(dest_dir, dest_filename)
        if not self.file_ops.exists(candidate):
            return candidate

        source_parent = (
            self.file_ops.basename(self.file_ops.dirname(filename)) or "collision"
        )
        collision_dir = self.file_ops.join(dest_dir, source_parent)
        collision_candidate = self.file_ops.join(collision_dir, dest_filename)
        collision_index = 1

        while self.file_ops.exists(collision_candidate):
            collision_dir = self.file_ops.join(
                dest_dir, f"{source_parent}.{collision_index}"
            )
            collision_candidate = self.file_ops.join(collision_dir, dest_filename)
            collision_index += 1

        if not self.file_ops.exists(collision_dir):
            self.file_ops.makedirs(collision_dir, exist_ok=True)

        return collision_candidate

    def _execute(
        self,
        process_parameters: dict,
        settings_dict: dict,
        filename: str,
        **kwargs,
    ) -> bool:
        """Copy file to destination directory.

        Args:
            process_parameters: Copy parameters with copy_to_directory
            settings_dict: Settings dictionary
            filename: File to copy

        Returns:
            True if copy was successful

        """
        dest_dir = process_parameters["copy_to_directory"]

        # Ensure destination directory exists
        if not self.file_ops.exists(dest_dir):
            try:
                self.file_ops.makedirs(dest_dir)
            except Exception as e:
                raise IOError(
                    f"Failed to create destination directory '{dest_dir}': {e}"
                )

        destination_path = self._resolve_destination(dest_dir, filename)
        self.file_ops.copy(filename, destination_path)
        return True

    def _get_backend_name(self) -> str:
        """Get backend name for logging."""
        return "copy"

    def _get_endpoint(self, process_parameters: dict, settings_dict: dict) -> str:
        """Get copy destination for logging."""
        return process_parameters.get("copy_to_directory", "")

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
        return self.execute(process_parameters, settings_dict, filename)

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
