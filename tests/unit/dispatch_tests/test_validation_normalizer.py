"""Tests for dispatch.pipeline.validator.normalize_validation_output.

Contract unification per specs/refactor-dispatch-simplification.md §3.4.
"""

import logging

import pytest

from dispatch.pipeline.validator import (
    ValidationResult,
    normalize_validation_output,
)


CURRENT_FILE = "/tmp/test.edi"


def test_tuple_two_element():
    """2-tuple passes through with first element coerced to bool."""
    assert normalize_validation_output((True, "new.edi"), CURRENT_FILE) == (True, "new.edi")
    assert normalize_validation_output((False, ["bad"]), CURRENT_FILE) == (False, ["bad"])


def test_tuple_three_element_rejected_gracefully():
    """Non-2-tuple must not raise TypeError; falls into unknown branch."""
    result = normalize_validation_output((True, "a.edi", "extra"), CURRENT_FILE)
    assert result[0] is False
    assert isinstance(result[1], list)
    assert "unexpected type" in result[1][0].lower() or "type" in result[1][0].lower()


def test_validation_result_invalid():
    vr = ValidationResult(is_valid=False, errors=["x", "y"])
    assert normalize_validation_output(vr, CURRENT_FILE) == (False, ["x", "y"])


def test_validation_result_valid():
    vr = ValidationResult(is_valid=True, errors=[])
    assert normalize_validation_output(vr, CURRENT_FILE) == (True, CURRENT_FILE)


def test_dict_valid():
    out = normalize_validation_output(
        {"valid": True, "file_path": "/x.edi"}, CURRENT_FILE
    )
    assert out == (True, "/x.edi")


def test_dict_invalid():
    out = normalize_validation_output(
        {"valid": False, "errors": ["bad"]}, CURRENT_FILE
    )
    assert out == (False, ["bad"])


def test_dict_valid_no_file_path_defaults_to_current():
    """When valid+True but no file_path, returns current_file."""
    assert normalize_validation_output({"valid": True}, CURRENT_FILE) == (True, CURRENT_FILE)


def test_bool_true():
    assert normalize_validation_output(True, CURRENT_FILE) == (True, CURRENT_FILE)


def test_bool_false():
    assert normalize_validation_output(False, CURRENT_FILE) == (False, CURRENT_FILE)


def test_unknown_logs_warning_and_returns_false(caplog):
    with caplog.at_level(logging.WARNING, logger="dispatch.pipeline.validator"):
        result = normalize_validation_output("a string", CURRENT_FILE)
    assert result[0] is False
    assert "unexpected type" in result[1][0].lower() or "type" in result[1][0].lower()
    assert any("str" in rec.message for rec in caplog.records)
