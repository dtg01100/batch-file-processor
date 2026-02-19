"""
Setup configuration for batch-file-processor.

This setup.py file makes the project installable and allows pytest
to discover and test the modules.
"""

from setuptools import setup, find_packages

with open("requirements.txt") as f:
    requirements = [
        line.strip() for line in f if line.strip() and not line.startswith("#")
    ]

setup(
    name="batch-file-processor",
    version="1.0.0",
    description="Batch file processor for EDI and CSV conversion",
    author="Development Team",
    python_requires=">=3.7",
    packages=find_packages(),
    py_modules=[
        "backup_increment",
        "batch_log_sender",
        "clear_old_files",
        "convert_to_csv",
        "convert_to_estore_einvoice_generic",
        "convert_to_estore_einvoice",
        "convert_to_fintech",
        "convert_to_jolley_custom",
        "convert_to_scannerware",
        "convert_to_scansheet_type_a",
        "convert_to_simplified_csv",
        "convert_to_stewarts_custom",
        "convert_to_yellowdog_csv",
        "copy_backend",
        "create_database",
        "database_import",
        "dialog",
        "_dispatch_legacy",
        "edi_tweaks",
        "email_backend",
        "folders_database_migrator",
        "ftp_backend",
        "mover",
        "mtc_edi_validator",
        "print_run_log",
        "query_runner",
        "record_error",
        "utils",
    ],
    install_requires=requirements,
    extras_require={
        "dev": [
            "pytest>=7.4.3",
            "pytest-cov>=4.1.0",
        ],
    },
    include_package_data=True,
)
