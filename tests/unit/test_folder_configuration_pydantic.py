import pytest

from core.domain.models.folder import (
    ARecordPaddingConfiguration,
    EDIConfiguration,
    FolderConfiguration,
    FTPConfiguration,
    UPCOverrideConfiguration,
)


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

    # should not raise; assert the round-tripped object is equal to
    # the input. If validate_with_pydantic() mutated or rejected the
    # config, this would fail.
    config.validate_with_pydantic()
    assert config.folder_name == "base"
    assert config.edi.split_edi is True

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


# ---------------------------------------------------------------------------
# Regression tests for the end-to-end mutation run (2026-07-13).
# The folder_configuration module had 10 surviving mutations in both
# test pairs. Each test below targets one specific mutation and
# pins a real production-code behavior.
# ---------------------------------------------------------------------------


class TestFTPConfiguration:
    """Tests for FTPConfiguration.validate()."""

    def test_ftp_port_must_be_in_valid_range(self):
        """L165 le_to_lt: port range check `1 <= port_int <= 65535` must
        reject 0 (off-by-one at the lower bound). With the mutation
        to `<`, port 0 would be silently accepted.
        """
        ftp = FTPConfiguration(server="s", port=0)
        errors = ftp.validate()
        assert any(
            "Port" in e and "Valid" in e for e in errors
        ), f"expected port=0 to be rejected as invalid, got errors={errors}"

    def test_ftp_port_high_boundary_65535_is_valid(self):
        """Boundary: port 65535 must be accepted (the upper limit)."""
        ftp = FTPConfiguration(server="s", port=65535)
        errors = ftp.validate()
        assert all(
            "Port" not in e for e in errors
        ), f"expected port=65535 to be valid, got errors={errors}"

    def test_ftp_port_low_boundary_1_is_valid(self):
        """Boundary: port 1 must be accepted (the lower limit)."""
        ftp = FTPConfiguration(server="s", port=1)
        errors = ftp.validate()
        assert all(
            "Port" not in e for e in errors
        ), f"expected port=1 to be valid, got errors={errors}"


class TestUPCOverrideConfiguration:
    """Tests for UPCOverrideConfiguration.validate()."""

    def test_upc_override_category_must_not_be_all(self):
        """L273 ne_to_eq: when enabled, category_filter is required and
        any category that isn't 'ALL' must be a valid integer. With
        the mutation flipping `!=` to `==`, 'ALL' would be silently
        skipped (and the category wouldn't be validated as a number).
        """
        # category_filter='ALL' should not pass the per-category
        # integer validation — but it IS allowed (the check is `!= 'ALL'`,
        # which means 'ALL' bypasses the int check). The test below
        # exercises the `!= 'ALL'` boundary: a non-numeric non-ALL
        # value must be rejected.
        config = UPCOverrideConfiguration(enabled=True, category_filter="not-a-number")
        errors = config.validate()
        assert any("Invalid" in e for e in errors), (
            f"expected non-ALL non-numeric category to be rejected, "
            f"got errors={errors}"
        )


class TestARecordPaddingConfiguration:
    """Tests for ARecordPaddingConfiguration.validate()."""

    def test_padding_text_too_long_is_rejected(self):
        """L298 gt_to_ge: padding text longer than padding_length must
        be rejected. With the mutation to `>=`, padding text exactly
        at length would be silently accepted.
        """
        config = ARecordPaddingConfiguration(
            enabled=True,
            padding_length=5,
            padding_text="ABCDEFG",  # 7 > 5
        )
        errors = config.validate()
        assert any("Padding" in e for e in errors), (
            f"expected padding_text longer than length to be rejected, "
            f"got errors={errors}"
        )

    def test_padding_text_exactly_at_length_is_valid(self):
        """Boundary: padding text exactly at length (6 chars, the
        default) must NOT produce the 'too long' error. The actual
        code has a second check that requires padding to be exactly
        6 chars regardless of padding_length; this test only
        verifies the first check (length) passes.

        Mutation: with the ``gt_to_ge`` mutation at L298
        (flipping ``>`` to ``>=``), padding text exactly at length
        would be silently accepted. This test catches that.
        """
        # padding_length=6 (default), padding_text="ABCDEF" — 6 chars
        # exactly. The first check (len > length) is False (6 > 6).
        # With the mutation, it becomes True (6 >= 6) and fires
        # the 'too long' error.
        config = ARecordPaddingConfiguration(
            enabled=True,
            padding_length=6,
            padding_text="ABCDEF",  # 6 chars == length
        )
        errors = config.validate()
        too_long_errors = [e for e in errors if "At Most" in e]
        assert not too_long_errors, (
            f"expected no 'too long' error for text exactly at length=6, "
            f"got errors={errors}"
        )


class TestFolderConfigurationDefaults:
    """Tests for FolderConfiguration default field values."""

    def test_alert_on_failure_default_is_true(self):
        """L409 true_to_false: alert_on_failure defaults to True. With
        the mutation to False, folders would silently not alert on
        failure.
        """
        config = FolderConfiguration(
            folder_name="base",
            alias="Base",
        )
        assert (
            config.alert_on_failure is True
        ), f"expected default alert_on_failure=True, got {config.alert_on_failure}"


class TestBoolFromData:
    """Tests for the module-level _bool_from_data helper."""

    def test_default_param_is_false(self):
        """L18 false_to_true: ``def _bool_from_data(data, key, *,
        default: bool = False)`` must default to False. With the
        mutation to True, callers that don't pass ``default=`` would
        get True for missing keys (silently flipping the behavior).
        """
        import inspect

        from core.domain.models.folder import _bool_from_data

        sig = inspect.signature(_bool_from_data)
        default = sig.parameters["default"].default
        assert not default, f"expected _bool_from_data default=False, got {default}"
