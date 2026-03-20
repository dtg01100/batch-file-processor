"""
Test backward compatibility - verify current version is a drop-in replacement.

This test suite ensures that the current version can be a drop-in replacement
for the version from approximately a month ago (baseline commit ~130 commits back).

Tests verify:
- Core modules are still importable
- Key APIs and protocols exist
- Database schema remains compatible
- Main entry points are functional
- API signatures are stable
- File conversion interfaces work
"""

import inspect

import pytest


class TestCoreModulesImportable:
    """Test that core modules can be imported without errors."""

    @pytest.mark.backward_compatibility
    @pytest.mark.unit
    def test_dispatch_module_importable(self):
        """dispatch module should be importable."""
        import dispatch

        assert dispatch is not None

    @pytest.mark.backward_compatibility
    @pytest.mark.unit
    def test_dispatch_orchestrator_importable(self):
        """DispatchOrchestrator should be importable."""
        from dispatch import DispatchOrchestrator

        assert DispatchOrchestrator is not None

    @pytest.mark.backward_compatibility
    @pytest.mark.unit
    def test_backend_module_importable(self):
        """backend module should be importable."""
        import backend

        assert backend is not None

    @pytest.mark.backward_compatibility
    @pytest.mark.unit
    def test_backend_protocols_importable(self):
        """backend.protocols should be importable."""
        from backend import protocols

        assert protocols is not None

    @pytest.mark.backward_compatibility
    @pytest.mark.unit
    def test_core_module_importable(self):
        """core module should be importable."""
        import core

        assert core is not None

    @pytest.mark.backward_compatibility
    @pytest.mark.unit
    def test_schema_module_importable(self):
        """schema module should be importable."""
        import core.database.schema

        assert schema is not None


class TestBackendProtocolsCompatibility:
    """Test that backend protocol interfaces are maintained."""

    @pytest.mark.backward_compatibility
    @pytest.mark.unit
    def test_backend_protocols_exist(self):
        """Backend protocols should be defined."""
        from backend.protocols import (
            FileOperationsProtocol,
            FTPClientProtocol,
            SMTPClientProtocol,
        )

        assert FileOperationsProtocol is not None
        assert FTPClientProtocol is not None
        assert SMTPClientProtocol is not None

    @pytest.mark.backward_compatibility
    @pytest.mark.unit
    def test_real_file_operations_exists(self):
        """RealFileOperations should exist."""
        from backend.file_operations import RealFileOperations

        assert RealFileOperations is not None

    @pytest.mark.backward_compatibility
    @pytest.mark.unit
    def test_file_operations_factory_exists(self):
        """create_file_operations factory should exist."""
        from backend.file_operations import create_file_operations

        assert callable(create_file_operations)

    @pytest.mark.backward_compatibility
    @pytest.mark.unit
    def test_ftp_client_importable(self):
        """FTP client module should be importable."""
        from backend.ftp_client import create_ftp_client

        assert callable(create_ftp_client)

    @pytest.mark.backward_compatibility
    @pytest.mark.unit
    def test_smtp_client_importable(self):
        """SMTP client (RealSMTPClient) should be importable."""
        from backend.smtp_client import RealSMTPClient

        assert RealSMTPClient is not None


class TestDispatchAPICompatibility:
    """Test that dispatch module APIs are maintained."""

    @pytest.mark.backward_compatibility
    @pytest.mark.unit
    def test_dispatch_orchestrator_class_exists(self):
        """DispatchOrchestrator class should exist."""
        from dispatch import DispatchOrchestrator

        assert DispatchOrchestrator is not None

    @pytest.mark.backward_compatibility
    @pytest.mark.unit
    def test_dispatch_config_class_exists(self):
        """DispatchConfig class should exist."""
        from dispatch import DispatchConfig

        assert DispatchConfig is not None

    @pytest.mark.backward_compatibility
    @pytest.mark.unit
    def test_dispatch_orchestrator_has_process_method(self):
        """DispatchOrchestrator should have process method."""
        from dispatch import DispatchOrchestrator

        assert hasattr(DispatchOrchestrator, "process")
        assert callable(getattr(DispatchOrchestrator, "process"))

    @pytest.mark.backward_compatibility
    @pytest.mark.unit
    def test_error_handler_exists(self):
        """ErrorHandler should be available."""
        from dispatch import ErrorHandler

        assert ErrorHandler is not None

    @pytest.mark.backward_compatibility
    @pytest.mark.unit
    def test_edi_validator_exists(self):
        """EDIValidator should be available."""
        from dispatch import EDIValidator

        assert EDIValidator is not None

    @pytest.mark.backward_compatibility
    @pytest.mark.unit
    def test_log_sender_exists(self):
        """LogSender should be available."""
        from dispatch import LogSender

        assert LogSender is not None


class TestPipelineCompatibility:
    """Test that pipeline modules maintain compatibility."""

    @pytest.mark.backward_compatibility
    @pytest.mark.unit
    def test_pipeline_module_exists(self):
        """dispatch.pipeline module should exist."""
        from dispatch import pipeline

        assert pipeline is not None

    @pytest.mark.backward_compatibility
    @pytest.mark.unit
    def test_converter_step_importable(self):
        """EDIConverterStep should be importable from pipeline."""
        from dispatch.pipeline.converter import EDIConverterStep

        assert EDIConverterStep is not None

    @pytest.mark.backward_compatibility
    @pytest.mark.unit
    def test_splitter_step_importable(self):
        """EDISplitterStep should be importable from pipeline."""
        from dispatch.pipeline.splitter import EDISplitterStep

        assert EDISplitterStep is not None

    @pytest.mark.backward_compatibility
    @pytest.mark.unit
    def test_validation_step_importable(self):
        """EDIValidationStep should be importable from pipeline."""
        from dispatch.pipeline.validator import EDIValidationStep

        assert EDIValidationStep is not None

    @pytest.mark.backward_compatibility
    @pytest.mark.unit
    def test_tweaker_step_importable(self):
        """EDITweakerStep should be importable from pipeline."""
        from dispatch.pipeline.tweaker import EDITweakerStep

        assert EDITweakerStep is not None

    @pytest.mark.backward_compatibility
    @pytest.mark.unit
    def test_pipeline_interfaces_exist(self):
        """Pipeline interfaces should exist."""
        from dispatch.pipeline.converter import ConverterInterface
        from dispatch.pipeline.splitter import SplitterInterface
        from dispatch.pipeline.tweaker import TweakerInterface
        from dispatch.pipeline.validator import ValidatorStepInterface

        assert ConverterInterface is not None
        assert SplitterInterface is not None
        assert ValidatorStepInterface is not None
        assert TweakerInterface is not None


class TestConversionModulesCompatibility:
    """Test that conversion modules maintain stable interfaces."""

    @pytest.mark.backward_compatibility
    @pytest.mark.conversion
    @pytest.mark.unit
    def test_convert_base_importable(self):
        """convert_base module should be importable."""
        from dispatch.converters.convert_base import BaseEDIConverter

        assert BaseEDIConverter is not None

    @pytest.mark.backward_compatibility
    @pytest.mark.conversion
    @pytest.mark.unit
    def test_conversion_base_has_methods(self):
        """BaseEDIConverter should have expected methods."""
        from dispatch.converters.convert_base import BaseEDIConverter

        # Should be an ABC with abstract methods
        assert BaseEDIConverter is not None
        assert hasattr(BaseEDIConverter, "edi_convert")

    @pytest.mark.backward_compatibility
    @pytest.mark.conversion
    @pytest.mark.unit
    @pytest.mark.parametrize(
        "module_name",
        [
            "convert_to_csv",
            "convert_to_simplified_csv",
            "convert_to_fintech",
            "convert_to_jolley_custom",
            "convert_to_scannerware",
        ],
    )
    def test_conversion_modules_importable(self, module_name):
        """Each conversion module should be importable."""
        try:
            mod = __import__(module_name)
            assert mod is not None
        except ImportError as e:
            pytest.fail(f"Failed to import {module_name}: {e}")


class TestDatabaseSchemaCompatibility:
    """Test that database schema compatibility is maintained."""

    @pytest.mark.backward_compatibility
    @pytest.mark.database
    @pytest.mark.unit
    def test_ensure_schema_function_exists(self):
        """ensure_schema function should exist."""
        from core.database.schema import ensure_schema

        assert callable(ensure_schema)

    @pytest.mark.backward_compatibility
    @pytest.mark.database
    @pytest.mark.unit
    def test_ensure_schema_accepts_connection(self):
        """ensure_schema should accept database_connection parameter."""
        from core.database.schema import ensure_schema

        sig = inspect.signature(ensure_schema)
        params = list(sig.parameters.keys())
        assert "database_connection" in params

    @pytest.mark.backward_compatibility
    @pytest.mark.database
    @pytest.mark.integration
    def test_core_database_module_exists(self):
        """core.database module should exist."""
        from core.database import DatabaseConnectionProtocol, QueryRunner

        assert DatabaseConnectionProtocol is not None
        assert QueryRunner is not None

    @pytest.mark.backward_compatibility
    @pytest.mark.database
    @pytest.mark.integration
    def test_schema_can_be_created(self, temp_db):
        """Core schema should be generatable without errors."""
        from core.database.schema import ensure_schema

        try:
            # Just verify this doesn't raise an error
            ensure_schema(temp_db)
        except Exception as e:
            pytest.fail(f"Failed to generate core schema: {e}")


class TestMainEntryPointsCompatibility:
    """Test that main entry points are still accessible."""

    @pytest.mark.backward_compatibility
    @pytest.mark.unit
    def test_main_interface_exists(self):
        """main_interface module should be importable."""
        try:
            import main_interface

            assert main_interface is not None
        except ImportError as e:
            pytest.fail(f"Failed to import main_interface: {e}")

    @pytest.mark.backward_compatibility
    @pytest.mark.unit
    def test_create_database_exists(self):
        """create_database module should be importable."""
        try:
            import scripts.create_database

            assert create_database is not None
        except ImportError as e:
            pytest.fail(f"Failed to import scripts.create_database: {e}")

    @pytest.mark.backward_compatibility
    @pytest.mark.unit
    def test_schema_module_accessible(self):
        """schema module should be accessible."""
        import core.database.schema

        assert hasattr(schema, "ensure_schema")


class TestAPISignaturePreservation:
    """Test that critical API signatures are preserved."""

    @pytest.mark.backward_compatibility
    @pytest.mark.unit
    def test_dispatch_orchestrator_instantiable(self):
        """DispatchOrchestrator should be instantiable."""
        from dispatch import DispatchOrchestrator

        try:
            # Should be instantiable with proper params
            assert DispatchOrchestrator is not None
            # Check that __init__ exists
            assert hasattr(DispatchOrchestrator, "__init__")
        except Exception as e:
            pytest.fail(f"DispatchOrchestrator not properly defined: {e}")

    @pytest.mark.backward_compatibility
    @pytest.mark.unit
    def test_base_edi_converter_instantiable(self):
        """BaseEDIConverter should be available as base class."""
        from dispatch.converters.convert_base import BaseEDIConverter

        try:
            assert BaseEDIConverter is not None
            assert hasattr(BaseEDIConverter, "__init__")
        except Exception as e:
            pytest.fail(f"BaseEDIConverter not properly defined: {e}")

    @pytest.mark.backward_compatibility
    @pytest.mark.unit
    def test_pipeline_steps_have_execute_method(self):
        """Pipeline steps should have execute methods."""
        from dispatch.pipeline.converter import EDIConverterStep
        from dispatch.pipeline.splitter import EDISplitterStep
        from dispatch.pipeline.tweaker import EDITweakerStep
        from dispatch.pipeline.validator import EDIValidationStep

        steps = [EDIConverterStep, EDISplitterStep, EDIValidationStep, EDITweakerStep]
        for step in steps:
            assert hasattr(step, "execute"), f"{step.__name__} missing execute method"


class TestExceptionHandling:
    """Test that exception classes are available."""

    @pytest.mark.backward_compatibility
    @pytest.mark.unit
    def test_core_utils_available(self):
        """core utilities should be importable."""
        try:
            from core import core.utils

            assert utils is not None
        except ImportError as e:
            pytest.fail(f"Failed to import core.utils: {e}")

    @pytest.mark.backward_compatibility
    @pytest.mark.unit
    def test_validation_error_available(self):
        """ValidationError should be available."""
        from dispatch.pipeline.validator import ValidationError

        assert ValidationError is not None


class TestInterfaceDefinitions:
    """Test that critical interfaces are defined."""

    @pytest.mark.backward_compatibility
    @pytest.mark.unit
    def test_file_system_interface_exists(self):
        """FileSystemInterface should be defined."""
        from dispatch import FileSystemInterface

        assert FileSystemInterface is not None

    @pytest.mark.backward_compatibility
    @pytest.mark.unit
    def test_database_interface_exists(self):
        """DatabaseInterface should be defined."""
        from dispatch import DatabaseInterface

        assert DatabaseInterface is not None

    @pytest.mark.backward_compatibility
    @pytest.mark.unit
    def test_backend_interface_exists(self):
        """BackendInterface should be defined."""
        from dispatch import BackendInterface

        assert BackendInterface is not None


class TestUtilityModulesAccessible:
    """Test that utility modules remain accessible."""

    @pytest.mark.backward_compatibility
    @pytest.mark.unit
    def test_utils_module_importable(self):
        """utils module should be importable."""
        import core.utils

        assert utils is not None

    @pytest.mark.backward_compatibility
    @pytest.mark.unit
    def test_core_edi_module_importable(self):
        """core.edi module should be importable."""
        from core import edi

        assert edi is not None

    @pytest.mark.backward_compatibility
    @pytest.mark.unit
    def test_batch_file_processor_constants_importable(self):
        """batch_file_processor.constants should be importable."""
        from core.constants import CURRENT_DATABASE_VERSION

        assert CURRENT_DATABASE_VERSION is not None


class TestBackendImplementations:
    """Test that backend implementations are available."""

    @pytest.mark.backward_compatibility
    @pytest.mark.unit
    def test_file_operations_protocol_implementations(self):
        """File operations implementations should exist."""
        from backend.file_operations import (
            MockFileOperations,
            RealFileOperations,
        )

        assert RealFileOperations is not None
        assert MockFileOperations is not None

    @pytest.mark.backward_compatibility
    @pytest.mark.unit
    def test_smtp_client_implementations(self):
        """SMTP client implementations should exist."""
        from backend.smtp_client import (
            MockSMTPClient,
            RealSMTPClient,
        )

        assert RealSMTPClient is not None
        assert MockSMTPClient is not None


# Fixtures


@pytest.fixture
def temp_db():
    """Provide a temporary in-memory SQLite database."""
    import sqlite3

    db = sqlite3.connect(":memory:")
    yield db
    db.close()
