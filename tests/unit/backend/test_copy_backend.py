"""Tests for the local copy backend."""

from backend.copy_backend import do
from backend.file_operations import MockFileOperations


def test_copy_backend_copies_to_expected_destination_file():
    file_ops = MockFileOperations()
    dest_dir = "/dest"
    src_file = "/tmp/output/example.csv"

    file_ops.add_directory(dest_dir)
    file_ops.add_file(src_file, "data")

    result = do({"copy_to_directory": dest_dir}, {}, src_file, file_ops=file_ops)

    assert result is True
    assert file_ops.files_copied == [(src_file, "/dest/example.csv")]
    assert file_ops.exists("/dest/example.csv")


def test_copy_backend_routes_duplicate_name_into_unique_subdirectory():
    file_ops = MockFileOperations()
    dest_dir = "/dest"
    src_file = "/tmp/edi_converter_abcd/eInvVendor.20260320201715.csv"
    existing_dest = "/dest/eInvVendor.20260320201715.csv"

    file_ops.add_directory(dest_dir)
    file_ops.add_file(src_file, "data")
    file_ops.add_existing_path(existing_dest)

    result = do({"copy_to_directory": dest_dir}, {}, src_file, file_ops=file_ops)

    assert result is True
    assert ("/dest/edi_converter_abcd", True) in file_ops.directories_created
    assert file_ops.files_copied == [
        (src_file, "/dest/edi_converter_abcd/eInvVendor.20260320201715.csv")
    ]


def test_copy_backend_uses_numbered_collision_directory_when_needed():
    file_ops = MockFileOperations()
    dest_dir = "/dest"
    src_file = "/tmp/edi_converter_abcd/eInvVendor.20260320201715.csv"

    file_ops.add_directory(dest_dir)
    file_ops.add_file(src_file, "data")
    file_ops.add_existing_path("/dest/eInvVendor.20260320201715.csv")
    file_ops.add_directory("/dest/edi_converter_abcd")
    file_ops.add_existing_path("/dest/edi_converter_abcd/eInvVendor.20260320201715.csv")

    result = do({"copy_to_directory": dest_dir}, {}, src_file, file_ops=file_ops)

    assert result is True
    assert ("/dest/edi_converter_abcd.1", True) in file_ops.directories_created
    assert file_ops.files_copied == [
        (src_file, "/dest/edi_converter_abcd.1/eInvVendor.20260320201715.csv")
    ]
