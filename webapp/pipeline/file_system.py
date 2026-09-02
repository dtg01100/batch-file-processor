"""File system abstraction for production use.

Provides a concrete implementation of FileSystemInterface using
Python's standard library, suitable for production environments.
Test implementations should use mock file systems instead.
"""

import os


class RealFileSystem:
    """Real file system implementation for production use."""

    def read_file(self, path: str) -> bytes:
        with open(path, "rb") as f:
            return f.read()

    def read_file_text(self, path: str, encoding: str = "utf-8") -> str:
        with open(path, encoding=encoding) as f:
            return f.read()

    def write_file(self, path: str, data: bytes) -> None:
        with open(path, "wb") as f:
            f.write(data)

    def write_file_text(self, path: str, data: str, encoding: str = "utf-8") -> None:
        with open(path, "w", encoding=encoding) as f:
            f.write(data)

    def file_exists(self, path: str) -> bool:
        return os.path.isfile(path)

    def dir_exists(self, path: str) -> bool:
        return os.path.isdir(path)

    def mkdir(self, path: str) -> None:
        os.mkdir(path)

    def makedirs(self, path: str) -> None:
        os.makedirs(path, exist_ok=True)

    def list_files(self, path: str) -> list[str]:
        if not os.path.isdir(path):
            return []
        return [
            os.path.abspath(os.path.join(path, f))
            for f in os.listdir(path)
            if os.path.isfile(os.path.join(path, f))
        ]

    def copy_file(self, src: str, dst: str) -> None:
        import shutil

        shutil.copyfile(src, dst)

    def remove_file(self, path: str) -> None:
        os.remove(path)

    def get_absolute_path(self, path: str) -> str:
        return os.path.abspath(path)
