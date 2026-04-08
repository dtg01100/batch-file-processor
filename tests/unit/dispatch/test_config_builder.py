"""Tests for DispatchConfigBuilder."""

from __future__ import annotations

from dispatch.config_builder import DispatchConfigBuilder, create_default_config
from dispatch.pipeline.validator import EDIValidationStep


class TestDispatchConfigBuilder:
    """Tests for DispatchConfigBuilder class."""

    def test_build_with_defaults(self):
        """Test building config with default values."""
        config = DispatchConfigBuilder().build()

        assert config.version == "1.0.0"
        assert config.settings == {}
        assert config.validator_step is None
        assert config.backends == {}

    def test_build_with_validator(self):
        """Test building config with validator step."""
        validator_step = EDIValidationStep()
        config = DispatchConfigBuilder().with_validator(validator_step).build()

        assert config.validator_step is validator_step

    def test_build_with_settings(self):
        """Test building config with settings."""
        settings = {"email_host": "smtp.example.com", "email_port": 587}
        config = DispatchConfigBuilder().with_settings(settings).build()

        assert config.settings == settings

    def test_build_with_version(self):
        """Test building config with version."""
        config = DispatchConfigBuilder().with_version("2.0.0").build()

        assert config.version == "2.0.0"

    def test_build_with_multiple_components(self):
        """Test building config with multiple components."""
        validator_step = EDIValidationStep()
        settings = {"test": "value"}

        config = (
            DispatchConfigBuilder()
            .with_validator(validator_step)
            .with_settings(settings)
            .with_version("3.0.0")
            .build()
        )

        assert config.validator_step is validator_step
        assert config.settings == settings
        assert config.version == "3.0.0"

    def test_add_backend_single(self):
        """Test adding a single backend."""
        mock_backend = object()

        config = DispatchConfigBuilder().add_backend("email", mock_backend).build()

        assert config.backends["email"] is mock_backend

    def test_add_multiple_backends_individually(self):
        """Test adding multiple backends one by one."""
        email_backend = object()
        ftp_backend = object()

        config = (
            DispatchConfigBuilder()
            .add_backend("email", email_backend)
            .add_backend("ftp", ftp_backend)
            .build()
        )

        assert config.backends["email"] is email_backend
        assert config.backends["ftp"] is ftp_backend

    def test_with_backends_dict(self):
        """Test setting all backends via dictionary."""
        backends = {"email": object(), "ftp": object(), "copy": object()}

        config = DispatchConfigBuilder().with_backends(backends).build()

        assert config.backends is backends

    def test_fluent_interface_returns_self(self):
        """Test that builder methods return self for chaining."""
        builder = DispatchConfigBuilder()

        result = builder.with_validator(EDIValidationStep())
        assert result is builder

        result = builder.with_settings({})
        assert result is builder

        result = builder.with_version("1.0.0")
        assert result is builder


class TestCreateDefaultConfig:
    """Tests for create_default_config helper."""

    def test_create_default_config_returns_config(self):
        """Test that create_default_config returns a valid config."""
        config = create_default_config()

        assert config is not None
        assert isinstance(config.version, str)
        assert isinstance(config.settings, dict)
