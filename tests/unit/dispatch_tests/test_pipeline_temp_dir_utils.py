from __future__ import annotations

import os
from types import SimpleNamespace

from dispatch.pipeline.temp_dir_utils import (
    cleanup_pipeline_temp_dir,
    create_pipeline_temp_dir,
)


def test_create_pipeline_temp_dir_registers_context_temp_dirs():
    temp_dirs: list[str] = []
    context = SimpleNamespace(temp_dirs=temp_dirs)
    folder: dict = {}

    temp_dir, returned_temp_dirs = create_pipeline_temp_dir(
        "edi_converter", folder, context
    )

    assert os.path.isdir(temp_dir)
    assert returned_temp_dirs is temp_dirs
    assert temp_dir in temp_dirs

    cleanup_pipeline_temp_dir(temp_dir, returned_temp_dirs)
    assert not os.path.exists(temp_dir)
    assert temp_dir not in temp_dirs


def test_create_pipeline_temp_dir_registers_folder_temp_dirs():
    temp_dirs: list[str] = []
    folder = {"_pipeline_temp_dirs": temp_dirs}

    temp_dir, returned_temp_dirs = create_pipeline_temp_dir(
        "edi_tweaker", folder, None
    )

    assert os.path.isdir(temp_dir)
    assert returned_temp_dirs is temp_dirs
    assert temp_dir in temp_dirs

    cleanup_pipeline_temp_dir(temp_dir, returned_temp_dirs)
    assert not os.path.exists(temp_dir)
    assert temp_dir not in temp_dirs


def test_cleanup_pipeline_temp_dir_handles_missing_tracking_list():
    temp_dir, returned_temp_dirs = create_pipeline_temp_dir(
        "edi_converter", {}, None
    )

    assert os.path.isdir(temp_dir)

    cleanup_pipeline_temp_dir(temp_dir, returned_temp_dirs)
    assert not os.path.exists(temp_dir)
