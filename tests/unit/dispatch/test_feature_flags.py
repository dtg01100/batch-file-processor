"""Unit tests for dispatch/feature_flags.py.

Tests:
- is_legacy_mode() returns correct value based on environment
- is_pipeline_enabled() returns correct value based on environment
- get_debug_mode() returns correct value based on environment
- get_feature_flags() returns all feature flags
- set_feature_flag() sets environment variable correctly
- set_feature_flag() raises error for unknown flag
- Feature flags are case-insensitive for true/false
- Feature flags default to correct values when not set
"""

import os

import pytest

from dispatch.feature_flags import (
    get_debug_mode,
    get_feature_flags,
    is_legacy_mode,
    is_pipeline_enabled,
    set_feature_flag,
)


class TestIsLegacyMode:
    """Test suite for is_legacy_mode()."""

    def test_default_false(self, monkeypatch):
        """Test that is_legacy_mode() defaults to False."""
        monkeypatch.delenv("USE_LEGACY_DISPATCH", raising=False)
        assert is_legacy_mode() is False

    def test_true_when_set_to_true(self, monkeypatch):
        """Test that is_legacy_mode() returns True when set to 'true'."""
        monkeypatch.setenv("USE_LEGACY_DISPATCH", "true")
        assert is_legacy_mode() is True

    def test_true_when_set_to_true_uppercase(self, monkeypatch):
        """Test that is_legacy_mode() returns True when set to 'TRUE'."""
        monkeypatch.setenv("USE_LEGACY_DISPATCH", "TRUE")
        assert is_legacy_mode() is True

    def test_true_when_set_to_true_mixed_case(self, monkeypatch):
        """Test that is_legacy_mode() returns True when set to 'TrUe'."""
        monkeypatch.setenv("USE_LEGACY_DISPATCH", "TrUe")
        assert is_legacy_mode() is True

    def test_false_when_set_to_false(self, monkeypatch):
        """Test that is_legacy_mode() returns False when set to 'false'."""
        monkeypatch.setenv("USE_LEGACY_DISPATCH", "false")
        assert is_legacy_mode() is False

    def test_false_when_set_to_false_uppercase(self, monkeypatch):
        """Test that is_legacy_mode() returns False when set to 'FALSE'."""
        monkeypatch.setenv("USE_LEGACY_DISPATCH", "FALSE")
        assert is_legacy_mode() is False

    def test_false_when_set_to_any_other_value(self, monkeypatch):
        """Test that is_legacy_mode() returns False for any other value."""
        monkeypatch.setenv("USE_LEGACY_DISPATCH", "random_value")
        assert is_legacy_mode() is False

    def test_false_when_set_to_number(self, monkeypatch):
        """Test that is_legacy_mode() returns False when set to a number."""
        monkeypatch.setenv("USE_LEGACY_DISPATCH", "1")
        assert is_legacy_mode() is False


class TestIsPipelineEnabled:
    """Test suite for is_pipeline_enabled()."""

    def test_default_true(self, monkeypatch):
        """Test that is_pipeline_enabled() defaults to True."""
        monkeypatch.delenv("DISPATCH_PIPELINE_ENABLED", raising=False)
        assert is_pipeline_enabled() is True

    def test_true_when_set_to_true(self, monkeypatch):
        """Test that is_pipeline_enabled() returns True when set to 'true'."""
        monkeypatch.setenv("DISPATCH_PIPELINE_ENABLED", "true")
        assert is_pipeline_enabled() is True

    def test_true_when_set_to_true_uppercase(self, monkeypatch):
        """Test that is_pipeline_enabled() returns True when set to 'TRUE'."""
        monkeypatch.setenv("DISPATCH_PIPELINE_ENABLED", "TRUE")
        assert is_pipeline_enabled() is True

    def test_false_when_set_to_false(self, monkeypatch):
        """Test that is_pipeline_enabled() returns False when set to 'false'."""
        monkeypatch.setenv("DISPATCH_PIPELINE_ENABLED", "false")
        assert is_pipeline_enabled() is False

    def test_false_when_set_to_false_uppercase(self, monkeypatch):
        """Test that is_pipeline_enabled() returns False when set to 'FALSE'."""
        monkeypatch.setenv("DISPATCH_PIPELINE_ENABLED", "FALSE")
        assert is_pipeline_enabled() is False

    def test_false_when_set_to_any_other_value(self, monkeypatch):
        """Test that is_pipeline_enabled() returns False for any other value."""
        monkeypatch.setenv("DISPATCH_PIPELINE_ENABLED", "random_value")
        assert is_pipeline_enabled() is False


class TestGetDebugMode:
    """Test suite for get_debug_mode()."""

    def test_default_false(self, monkeypatch):
        """Test that get_debug_mode() defaults to False."""
        monkeypatch.delenv("DISPATCH_DEBUG_MODE", raising=False)
        assert get_debug_mode() is False

    def test_true_when_set_to_true(self, monkeypatch):
        """Test that get_debug_mode() returns True when set to 'true'."""
        monkeypatch.setenv("DISPATCH_DEBUG_MODE", "true")
        assert get_debug_mode() is True

    def test_true_when_set_to_true_uppercase(self, monkeypatch):
        """Test that get_debug_mode() returns True when set to 'TRUE'."""
        monkeypatch.setenv("DISPATCH_DEBUG_MODE", "TRUE")
        assert get_debug_mode() is True

    def test_false_when_set_to_false(self, monkeypatch):
        """Test that get_debug_mode() returns False when set to 'false'."""
        monkeypatch.setenv("DISPATCH_DEBUG_MODE", "false")
        assert get_debug_mode() is False

    def test_false_when_set_to_false_uppercase(self, monkeypatch):
        """Test that get_debug_mode() returns False when set to 'FALSE'."""
        monkeypatch.setenv("DISPATCH_DEBUG_MODE", "FALSE")
        assert get_debug_mode() is False

    def test_false_when_set_to_any_other_value(self, monkeypatch):
        """Test that get_debug_mode() returns False for any other value."""
        monkeypatch.setenv("DISPATCH_DEBUG_MODE", "random_value")
        assert get_debug_mode() is False


class TestGetFeatureFlags:
    """Test suite for get_feature_flags()."""

    def test_returns_all_flags_default_values(self, monkeypatch):
        """Test that get_feature_flags() returns all flags with default values."""
        monkeypatch.delenv("USE_LEGACY_DISPATCH", raising=False)
        monkeypatch.delenv("DISPATCH_PIPELINE_ENABLED", raising=False)
        monkeypatch.delenv("DISPATCH_DEBUG_MODE", raising=False)

        flags = get_feature_flags()

        assert flags == {
            "legacy_mode": False,
            "pipeline_enabled": True,
            "debug_mode": False,
        }

    def test_returns_all_flags_custom_values(self, monkeypatch):
        """Test that get_feature_flags() returns all flags with custom values."""
        monkeypatch.setenv("USE_LEGACY_DISPATCH", "true")
        monkeypatch.setenv("DISPATCH_PIPELINE_ENABLED", "false")
        monkeypatch.setenv("DISPATCH_DEBUG_MODE", "true")

        flags = get_feature_flags()

        assert flags == {
            "legacy_mode": True,
            "pipeline_enabled": False,
            "debug_mode": True,
        }

    def test_returns_all_flags_mixed_values(self, monkeypatch):
        """Test that get_feature_flags() returns all flags with mixed values."""
        monkeypatch.setenv("USE_LEGACY_DISPATCH", "true")
        monkeypatch.delenv("DISPATCH_PIPELINE_ENABLED", raising=False)
        monkeypatch.setenv("DISPATCH_DEBUG_MODE", "false")

        flags = get_feature_flags()

        assert flags == {
            "legacy_mode": True,
            "pipeline_enabled": True,  # Default
            "debug_mode": False,
        }

    def test_flags_are_dictionary(self, monkeypatch):
        """Test that get_feature_flags() returns a dictionary."""
        flags = get_feature_flags()
        assert isinstance(flags, dict)

    def test_flags_have_correct_keys(self, monkeypatch):
        """Test that get_feature_flags() returns dictionary with correct keys."""
        flags = get_feature_flags()
        expected_keys = {"legacy_mode", "pipeline_enabled", "debug_mode"}
        assert set(flags.keys()) == expected_keys


class TestSetFeatureFlag:
    """Test suite for set_feature_flag()."""

    def test_set_legacy_mode_true(self, monkeypatch):
        """Test setting legacy_mode to True."""
        set_feature_flag("legacy_mode", True)
        assert os.environ.get("USE_LEGACY_DISPATCH") == "true"
        assert is_legacy_mode() is True

    def test_set_legacy_mode_false(self, monkeypatch):
        """Test setting legacy_mode to False."""
        set_feature_flag("legacy_mode", False)
        assert os.environ.get("USE_LEGACY_DISPATCH") == "false"
        assert is_legacy_mode() is False

    def test_set_pipeline_enabled_true(self, monkeypatch):
        """Test setting pipeline_enabled to True."""
        set_feature_flag("pipeline_enabled", True)
        assert os.environ.get("DISPATCH_PIPELINE_ENABLED") == "true"
        assert is_pipeline_enabled() is True

    def test_set_pipeline_enabled_false(self, monkeypatch):
        """Test setting pipeline_enabled to False."""
        set_feature_flag("pipeline_enabled", False)
        assert os.environ.get("DISPATCH_PIPELINE_ENABLED") == "false"
        assert is_pipeline_enabled() is False

    def test_set_debug_mode_true(self, monkeypatch):
        """Test setting debug_mode to True."""
        set_feature_flag("debug_mode", True)
        assert os.environ.get("DISPATCH_DEBUG_MODE") == "true"
        assert get_debug_mode() is True

    def test_set_debug_mode_false(self, monkeypatch):
        """Test setting debug_mode to False."""
        set_feature_flag("debug_mode", False)
        assert os.environ.get("DISPATCH_DEBUG_MODE") == "false"
        assert get_debug_mode() is False

    def test_set_unknown_flag_raises_error(self):
        """Test that setting unknown flag raises ValueError."""
        with pytest.raises(ValueError) as exc_info:
            set_feature_flag("unknown_flag", True)

        assert "Unknown feature flag" in str(exc_info.value)
        assert "unknown_flag" in str(exc_info.value)

    def test_set_unknown_flag_error_message_includes_valid_flags(self):
        """Test that error message includes list of valid flags."""
        with pytest.raises(ValueError) as exc_info:
            set_feature_flag("unknown_flag", True)

        error_msg = str(exc_info.value)
        assert "legacy_mode" in error_msg
        assert "pipeline_enabled" in error_msg
        assert "debug_mode" in error_msg

    def test_overwrite_existing_flag(self, monkeypatch):
        """Test that set_feature_flag() overwrites existing value."""
        monkeypatch.setenv("USE_LEGACY_DISPATCH", "false")
        set_feature_flag("legacy_mode", True)
        assert os.environ.get("USE_LEGACY_DISPATCH") == "true"

    def test_set_flag_affects_get_feature_flags(self, monkeypatch):
        """Test that set_feature_flag() affects get_feature_flags() result."""
        set_feature_flag("legacy_mode", True)
        flags = get_feature_flags()
        assert flags["legacy_mode"] is True


class TestFeatureFlagsIntegration:
    """Integration tests for feature flags."""

    def test_multiple_flags_can_be_set(self, monkeypatch):
        """Test that multiple flags can be set independently."""
        set_feature_flag("legacy_mode", True)
        set_feature_flag("pipeline_enabled", False)
        set_feature_flag("debug_mode", True)

        assert is_legacy_mode() is True
        assert is_pipeline_enabled() is False
        assert get_debug_mode() is True

    def test_flags_are_independent(self, monkeypatch):
        """Test that flags are independent of each other."""
        monkeypatch.setenv("USE_LEGACY_DISPATCH", "true")
        monkeypatch.setenv("DISPATCH_PIPELINE_ENABLED", "false")
        monkeypatch.setenv("DISPATCH_DEBUG_MODE", "true")

        # Verify all flags have their independent values
        assert is_legacy_mode() is True
        assert is_pipeline_enabled() is False
        assert get_debug_mode() is True

    def test_get_feature_flags_reflects_current_state(self, monkeypatch):
        """Test that get_feature_flags() reflects current environment state."""
        # Set via environment variable
        monkeypatch.setenv("USE_LEGACY_DISPATCH", "true")
        flags = get_feature_flags()
        assert flags["legacy_mode"] is True

        # Set via set_feature_flag
        set_feature_flag("legacy_mode", False)
        flags = get_feature_flags()
        assert flags["legacy_mode"] is False

    def test_default_behavior_without_any_env_vars(self, monkeypatch):
        """Test default behavior when no environment variables are set."""
        monkeypatch.delenv("USE_LEGACY_DISPATCH", raising=False)
        monkeypatch.delenv("DISPATCH_PIPELINE_ENABLED", raising=False)
        monkeypatch.delenv("DISPATCH_DEBUG_MODE", raising=False)

        assert is_legacy_mode() is False
        assert is_pipeline_enabled() is True
        assert get_debug_mode() is False

        flags = get_feature_flags()
        assert flags == {
            "legacy_mode": False,
            "pipeline_enabled": True,
            "debug_mode": False,
        }

    def test_string_values_are_normalized(self, monkeypatch):
        """Test that string values are normalized to lowercase before comparison."""
        # These should all be treated as 'true'
        for value in ["true", "TRUE", "True", "TrUe", "tRuE"]:
            monkeypatch.setenv("USE_LEGACY_DISPATCH", value)
            assert is_legacy_mode() is True

        # These should all be treated as 'false'
        for value in ["false", "FALSE", "False", "FaLsE", "fAlSe"]:
            monkeypatch.setenv("USE_LEGACY_DISPATCH", value)
            assert is_legacy_mode() is False

    def test_environment_variable_names_are_correct(self, monkeypatch):
        """Test that the correct environment variable names are used."""
        set_feature_flag("legacy_mode", True)
        assert "USE_LEGACY_DISPATCH" in os.environ

        set_feature_flag("pipeline_enabled", True)
        assert "DISPATCH_PIPELINE_ENABLED" in os.environ

        set_feature_flag("debug_mode", True)
        assert "DISPATCH_DEBUG_MODE" in os.environ


class TestFeatureFlagsUseCases:
    """Test realistic use cases for feature flags."""

    def test_enable_legacy_mode_for_migration(self, monkeypatch):
        """Test enabling legacy mode for migration scenario."""
        set_feature_flag("legacy_mode", True)
        set_feature_flag("pipeline_enabled", False)

        assert is_legacy_mode() is True
        assert is_pipeline_enabled() is False

    def test_enable_debug_mode_for_troubleshooting(self, monkeypatch):
        """Test enabling debug mode for troubleshooting."""
        set_feature_flag("debug_mode", True)

        assert get_debug_mode() is True

    def test_new_system_with_all_flags_default(self, monkeypatch):
        """Test new system with all flags at default values."""
        monkeypatch.delenv("USE_LEGACY_DISPATCH", raising=False)
        monkeypatch.delenv("DISPATCH_PIPELINE_ENABLED", raising=False)
        monkeypatch.delenv("DISPATCH_DEBUG_MODE", raising=False)

        # Default: use new pipeline, not legacy, no debug
        assert is_legacy_mode() is False
        assert is_pipeline_enabled() is True
        assert get_debug_mode() is False

    def test_mixed_scenario_with_custom_flags(self, monkeypatch):
        """Test mixed scenario with some custom flags."""
        # Custom: enable debug, use pipeline, not legacy
        monkeypatch.delenv("DISPATCH_PIPELINE_ENABLED", raising=False)
        monkeypatch.setenv("DISPATCH_DEBUG_MODE", "true")
        monkeypatch.setenv("USE_LEGACY_DISPATCH", "false")
        # Pipeline enabled by default

        assert is_legacy_mode() is False
        assert is_pipeline_enabled() is True
        assert get_debug_mode() is True

    def test_disable_pipeline_for_testing(self, monkeypatch):
        """Test disabling pipeline for testing legacy code path."""
        set_feature_flag("pipeline_enabled", False)
        assert is_pipeline_enabled() is False
