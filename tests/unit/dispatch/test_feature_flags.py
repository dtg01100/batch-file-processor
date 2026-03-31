"""Unit tests for dispatch/feature_flags.py after hard cutover.

Supported feature flags are DISPATCH_DEBUG_MODE and DISPATCH_STRICT_TESTING_MODE.
"""

import os

import pytest

from dispatch.feature_flags import (
    get_debug_mode,
    get_feature_flags,
    get_strict_testing_mode,
    set_feature_flag,
)


class TestGetDebugMode:
    """Test suite for get_debug_mode()."""

    def test_default_false(self, monkeypatch):
        monkeypatch.delenv("DISPATCH_DEBUG_MODE", raising=False)
        assert get_debug_mode() is False

    def test_true_when_set_to_true_case_insensitive(self, monkeypatch):
        for value in ["true", "TRUE", "TrUe"]:
            monkeypatch.setenv("DISPATCH_DEBUG_MODE", value)
            assert get_debug_mode() is True

    def test_false_for_false_or_other_values(self, monkeypatch):
        for value in ["false", "FALSE", "random_value", "1"]:
            monkeypatch.setenv("DISPATCH_DEBUG_MODE", value)
            assert get_debug_mode() is False


class TestGetFeatureFlags:
    """Test suite for get_feature_flags()."""

    def test_returns_debug_only_default(self, monkeypatch):
        monkeypatch.delenv("DISPATCH_DEBUG_MODE", raising=False)
        monkeypatch.delenv("DISPATCH_STRICT_TESTING_MODE", raising=False)
        assert get_feature_flags() == {
            "debug_mode": False,
            "strict_testing_mode": False,
        }

    def test_returns_debug_only_custom(self, monkeypatch):
        monkeypatch.setenv("DISPATCH_DEBUG_MODE", "true")
        monkeypatch.setenv("DISPATCH_STRICT_TESTING_MODE", "true")
        assert get_feature_flags() == {
            "debug_mode": True,
            "strict_testing_mode": True,
        }


class TestGetStrictTestingMode:
    """Test suite for get_strict_testing_mode()."""

    def test_pytest_enables_strict_testing_mode(self):
        assert os.environ.get("DISPATCH_STRICT_TESTING_MODE") == "true"
        assert get_strict_testing_mode() is True

    def test_default_false(self, monkeypatch):
        monkeypatch.delenv("DISPATCH_STRICT_TESTING_MODE", raising=False)
        assert get_strict_testing_mode() is False

    def test_true_when_set_to_true_case_insensitive(self, monkeypatch):
        for value in ["true", "TRUE", "TrUe"]:
            monkeypatch.setenv("DISPATCH_STRICT_TESTING_MODE", value)
            assert get_strict_testing_mode() is True

    def test_false_for_false_or_other_values(self, monkeypatch):
        for value in ["false", "FALSE", "random_value", "1"]:
            monkeypatch.setenv("DISPATCH_STRICT_TESTING_MODE", value)
            assert get_strict_testing_mode() is False


class TestSetFeatureFlag:
    """Test suite for set_feature_flag()."""

    def test_set_debug_mode_true(self, monkeypatch):
        monkeypatch.delenv("DISPATCH_DEBUG_MODE", raising=False)
        set_feature_flag("debug_mode", value=True)
        assert os.environ.get("DISPATCH_DEBUG_MODE") == "true"
        assert get_debug_mode() is True

    def test_set_debug_mode_false(self, monkeypatch):
        monkeypatch.delenv("DISPATCH_DEBUG_MODE", raising=False)
        set_feature_flag("debug_mode", value=False)
        assert os.environ.get("DISPATCH_DEBUG_MODE") == "false"
        assert get_debug_mode() is False

    def test_set_strict_testing_mode_true(self, monkeypatch):
        monkeypatch.delenv("DISPATCH_STRICT_TESTING_MODE", raising=False)
        set_feature_flag("strict_testing_mode", value=True)
        assert os.environ.get("DISPATCH_STRICT_TESTING_MODE") == "true"
        assert get_strict_testing_mode() is True

    def test_set_strict_testing_mode_false(self, monkeypatch):
        monkeypatch.delenv("DISPATCH_STRICT_TESTING_MODE", raising=False)
        set_feature_flag("strict_testing_mode", value=False)
        assert os.environ.get("DISPATCH_STRICT_TESTING_MODE") == "false"
        assert get_strict_testing_mode() is False

    @pytest.mark.parametrize(
        "unknown_flag", ["legacy_mode", "pipeline_enabled", "unknown_flag"]
    )
    def test_unknown_flag_raises_error(self, unknown_flag):
        with pytest.raises(ValueError) as exc_info:
            set_feature_flag(unknown_flag, value=True)

        error_msg = str(exc_info.value)
        assert "Unknown feature flag" in error_msg
        assert "debug_mode" in error_msg
        assert "strict_testing_mode" in error_msg
