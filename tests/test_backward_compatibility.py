"""Smoke tests for backward compatibility.

Verifies that core modules, classes, and functions remain importable
and have expected interfaces. These are smoke tests, not full functional tests.
"""

import pytest


class TestCoreModulesImportable:
    """Smoke tests for core module imports."""

    @pytest.mark.backward_compatibility
    @pytest.mark.unit
    @pytest.mark.parametrize(
        "module_name",
        [
            "dispatch",
            "backend",
            "core",
        ],
    )
    def test_core_module_importable(self, module_name):
        mod = __import__(module_name)
        assert mod is not None


class TestCriticalClassesImportable:
    """Smoke tests for critical class imports."""

    @pytest.mark.backward_compatibility
    @pytest.mark.unit
    @pytest.mark.parametrize(
        "import_path,class_name",
        [
            ("dispatch", "DispatchOrchestrator"),
            ("dispatch", "DispatchConfig"),
            ("dispatch", "ErrorHandler"),
            ("dispatch", "EDIValidator"),
            ("dispatch", "LogSender"),
            ("backend.protocols", "FileOperationsProtocol"),
            ("backend.protocols", "FTPClientProtocol"),
            ("backend.protocols", "SMTPClientProtocol"),
            ("backend.file_operations", "RealFileOperations"),
            ("backend.file_operations", "MockFileOperations"),
            ("backend.smtp_client", "RealSMTPClient"),
            ("backend.smtp_client", "MockSMTPClient"),
            ("dispatch.converters.convert_base", "BaseEDIConverter"),
            ("dispatch.pipeline.converter", "EDIConverterStep"),
            ("dispatch.pipeline.splitter", "EDISplitterStep"),
            ("dispatch.pipeline.validator", "EDIValidationStep"),
            ("dispatch.pipeline.tweaker", "EDITweakerStep"),
            ("dispatch.pipeline.converter", "ConverterInterface"),
            ("dispatch.pipeline.splitter", "SplitterInterface"),
            ("dispatch.pipeline.validator", "ValidatorStepInterface"),
            ("dispatch.pipeline.tweaker", "TweakerInterface"),
        ],
    )
    def test_critical_class_importable(self, import_path, class_name):
        module = __import__(import_path, fromlist=[class_name])
        cls = getattr(module, class_name)
        assert cls is not None


class TestCriticalFunctionsImportable:
    """Smoke tests for critical function imports."""

    @pytest.mark.backward_compatibility
    @pytest.mark.unit
    @pytest.mark.parametrize(
        "import_path,func_name",
        [
            ("backend.file_operations", "create_file_operations"),
            ("backend.ftp_client", "create_ftp_client"),
            ("core.database.schema", "ensure_schema"),
        ],
    )
    def test_critical_function_importable(self, import_path, func_name):
        module = __import__(import_path, fromlist=[func_name])
        func = getattr(module, func_name)
        assert callable(func)


class TestDispatchInterfaces:
    """Smoke tests for dispatch interfaces."""

    @pytest.mark.backward_compatibility
    @pytest.mark.unit
    @pytest.mark.parametrize(
        "interface_name",
        [
            "FileSystemInterface",
            "DatabaseInterface",
            "BackendInterface",
        ],
    )
    def test_dispatch_interface_exists(self, interface_name):
        import dispatch

        iface = getattr(dispatch, interface_name)
        assert iface is not None


class TestPipelineStepInterfaces:
    """Smoke tests for pipeline step interfaces."""

    @pytest.mark.backward_compatibility
    @pytest.mark.unit
    @pytest.mark.parametrize(
        "interface_path,interface_name",
        [
            ("dispatch.pipeline.converter", "ConverterInterface"),
            ("dispatch.pipeline.splitter", "SplitterInterface"),
            ("dispatch.pipeline.validator", "ValidatorStepInterface"),
            ("dispatch.pipeline.tweaker", "TweakerInterface"),
        ],
    )
    def test_pipeline_interface_exists(self, interface_path, interface_name):
        module = __import__(interface_path, fromlist=[interface_name])
        iface = getattr(module, interface_name)
        assert iface is not None


class TestConversionModulesImportable:
    """Smoke tests for conversion module imports."""

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
    def test_conversion_module_importable(self, module_name):
        mod = __import__(
            f"dispatch.converters.{module_name}", fromlist=["dispatch.converters"]
        )
        assert mod is not None


class TestDatabaseSchemaFunctions:
    """Smoke tests for database schema functions."""

    @pytest.mark.backward_compatibility
    @pytest.mark.database
    @pytest.mark.unit
    def test_ensure_schema_exists(self):
        from core.database.schema import ensure_schema

        assert callable(ensure_schema)

    @pytest.mark.backward_compatibility
    @pytest.mark.database
    @pytest.mark.unit
    def test_ensure_schema_accepts_connection(self):
        import inspect

        from core.database.schema import ensure_schema

        sig = inspect.signature(ensure_schema)
        params = list(sig.parameters.keys())
        assert "database_connection" in params


class TestMainEntryPoints:
    """Smoke tests for main entry points."""

    @pytest.mark.backward_compatibility
    @pytest.mark.unit
    def test_main_interface_importable(self):
        import main_interface

        assert main_interface is not None

    @pytest.mark.backward_compatibility
    @pytest.mark.unit
    def test_schema_module_accessible(self):
        from core.database import schema

        assert hasattr(schema, "ensure_schema")


class TestCoreUtilities:
    """Smoke tests for core utilities."""

    @pytest.mark.backward_compatibility
    @pytest.mark.unit
    def test_utils_module_importable(self):
        import core.utils

        assert core.utils is not None

    @pytest.mark.backward_compatibility
    @pytest.mark.unit
    def test_core_edi_module_importable(self):
        from core import edi

        assert edi is not None

    @pytest.mark.backward_compatibility
    @pytest.mark.unit
    def test_batch_file_processor_constants_importable(self):
        from core.constants import CURRENT_DATABASE_VERSION

        assert CURRENT_DATABASE_VERSION is not None

    @pytest.mark.backward_compatibility
    @pytest.mark.unit
    def test_validation_error_available(self):
        from dispatch.pipeline.validator import ValidationError

        assert ValidationError is not None


class TestPipelineStepExecuteMethod:
    """Smoke tests for pipeline steps having execute method."""

    @pytest.mark.backward_compatibility
    @pytest.mark.unit
    @pytest.mark.parametrize(
        "step_class",
        [
            "EDIConverterStep",
            "EDISplitterStep",
            "EDIValidationStep",
            "EDITweakerStep",
        ],
    )
    def test_pipeline_step_has_execute_method(self, step_class):
        from dispatch.pipeline.converter import EDIConverterStep
        from dispatch.pipeline.splitter import EDISplitterStep
        from dispatch.pipeline.tweaker import EDITweakerStep
        from dispatch.pipeline.validator import EDIValidationStep

        step_map = {
            "EDIConverterStep": EDIConverterStep,
            "EDISplitterStep": EDISplitterStep,
            "EDIValidationStep": EDIValidationStep,
            "EDITweakerStep": EDITweakerStep,
        }
        step = step_map[step_class]
        assert hasattr(step, "execute"), f"{step_class} missing execute method"
