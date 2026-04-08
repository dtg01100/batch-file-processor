import pytest

from interface.models.folder_configuration import EDIConfiguration, FolderConfiguration


def test_folder_configuration_pydantic_valid():
    config = FolderConfiguration(
        folder_name="base",
        alias="Base",
        edi=EDIConfiguration(
            process_edi=True,
            split_edi=True,
            prepend_date_files=True,
        ),
    )

    # should not raise
    config.validate_with_pydantic()


def test_folder_configuration_pydantic_invalid_prepend_date_without_split():
    config = FolderConfiguration(
        folder_name="bad",
        alias="Bad",
        edi=EDIConfiguration(
            process_edi=True,
            split_edi=False,
            prepend_date_files=True,
        ),
    )

    with pytest.raises(ValueError, match="prepend_date_files requires split_edi"):
        config.validate_with_pydantic()


def test_folder_configuration_from_dict_uses_pydantic_validation():
    data = {
        "folder_name": "bad",
        "alias": "Bad",
        "process_edi": True,
        "split_edi": False,
        "prepend_date_files": True,
    }

    with pytest.raises(ValueError, match="pydantic validation failed"):
        FolderConfiguration.from_dict(data)
