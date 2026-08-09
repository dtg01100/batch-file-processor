"""Pipeline steps for dispatch processing.

This module contains the individual pipeline steps that make up
the file processing pipeline in the dispatch system.

IMPORT NOTE (import cycle): this package eagerly re-exports its submodules,
so ANY ``import dispatch.pipeline.<submodule>`` runs this whole file first.
In particular, it pulls in ``dispatch.pipeline.factory``, which imports
``dispatch.results``. That is only safe because ``dispatch.results`` is a
leaf module (see its IMPORT NOTE and ``docs/IMPORT_ARCHITECTURE.md``); it
must stay that way, and ``dispatch.services.*`` must not
module-level-import this package.
"""

from dispatch.pipeline.converter import (
    SUPPORTED_FORMATS,
    ConverterInterface,
    ConverterResult,
    DefaultModuleLoader,
    EDIConverterStep,
    MockConverter,
    ModuleLoaderProtocol,
)
from dispatch.pipeline.factory import (
    create_standard_pipeline,
)
from dispatch.pipeline.splitter import (
    CreditDetectorProtocol,
    DefaultCreditDetector,
    EDISplitterStep,
    MockSplitter,
    SplitterInterface,
    SplitterResult,
)
from dispatch.pipeline.validator import (
    EDIValidationStep,
    MockValidator,
    ValidationError,
    ValidationResult,
    ValidatorStepInterface,
)

__all__ = [
    "SUPPORTED_FORMATS",
    "ConverterInterface",
    # Converter
    "ConverterResult",
    "CreditDetectorProtocol",
    "DefaultCreditDetector",
    "DefaultModuleLoader",
    "EDIConverterStep",
    "EDISplitterStep",
    "EDIValidationStep",
    "MockConverter",
    "MockSplitter",
    "MockValidator",
    "ModuleLoaderProtocol",
    "SplitterInterface",
    # Splitter
    "SplitterResult",
    "ValidationError",
    # Validator
    "ValidationResult",
    "ValidatorStepInterface",
    # Factory
    "create_standard_pipeline",
]
