"""Smoke test: vendored 1.47 ``dispatch`` module loads under the harness stubs.

This is a single fast test that proves the conftest fixture actually installs
the stubs, registers ImageOps, prepends the vendored dir to ``sys.path``, and
imports the vendored ``dispatch`` module without exploding. If this test ever
fails the per-row routing test below will likely also fail in confusing ways
— fix this one first.
"""
from __future__ import annotations

import importlib


def test_vendored_dispatch_imports(legacy_147_dispatch):
    assert legacy_147_dispatch is not None
    # The vendored dispatch must define ``process`` (it's the function we
    # drive end-to-end below).
    assert callable(getattr(legacy_147_dispatch, "process", None))


def test_vendored_convert_to_csv_imports():
    """``convert_to_csv`` is one of the simplest 1.47 converters — if it
    imports, the harness's sys.path + stubs setup is correct."""
    mod = importlib.import_module("convert_to_csv")
    assert hasattr(mod, "edi_convert")


def test_imageops_shim_available(_legacy_147_runtime):
    import sys

    if "ImageOps" in sys.modules:
        # The shim is registered when PIL is importable. Verify the alias
        # resolves to a PIL.ImageOps mirror.
        import PIL.ImageOps as ref

        assert sys.modules["ImageOps"].__dict__ == ref.__dict__
    else:
        # PIL unavailable — convert_to_scansheet_type_a tests will skip.
        import pytest

        pytest.skip("PIL not available; convert_to_scansheet_type_a tests will skip")
