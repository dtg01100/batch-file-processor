"""
Performance Benchmark Script for Batch File Processor Converters.

This script benchmarks the performance of various EDI converter plugins
by processing a generated synthetic EDI file.
"""

import importlib
import os
import sys
import tempfile
import time
from unittest.mock import MagicMock, patch

# Ensure project root is in path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# Converters to benchmark
CONVERTERS = [
    "convert_to_csv",
    "convert_to_fintech",
    "convert_to_scannerware",
    "convert_to_edi_tweaks",
    # Add others as needed
]

# Benchmark configuration
RECORD_COUNT = 5000  # Number of B records
ITERATIONS = 3  # Number of runs per converter


def generate_edi_data(filename, record_count):
    """Generate a synthetic EDI file."""
    with open(filename, "w") as f:
        # Header (A Record)
        # Type(1), Cust(6), Inv(10), Date(6), Total(10)
        f.write("A12345612345678900101230000012345\n")

        # Items (B Records)
        for i in range(record_count):
            # Construct B record matching standard format (76 chars)
            # Type (1)
            b_rec = "B"
            # UPC (11)
            b_rec += f"{i:011d}"
            # Description (25)
            b_rec += f"Test Item {i}".ljust(25)[:25]
            # Vendor Item (6)
            b_rec += "123456"
            # Unit Cost (6)
            b_rec += "001000"
            # Combo Code (2)
            b_rec += "00"
            # Unit Multiplier (6)
            b_rec += "000001"
            # Qty (5)
            b_rec += "00001"
            # Retail (5)
            b_rec += "00200"
            # Price Multi Pack (3)
            b_rec += "000"
            # Parent Item (6)
            b_rec += "000000"

            f.write(b_rec + "\n")

        # Footer/Charges (C Records)
        # Type(1), Code(3), Desc(25), Amount(9)
        f.write("C123Test Charge              000001000\n")


def run_benchmark():
    print(f"Starting benchmark with {RECORD_COUNT} records per file...")
    print(f"{'Converter':<25} | {'Avg Time (s)':<12} | {'Rate (rec/s)':<12}")
    print("-" * 55)

    with tempfile.TemporaryDirectory() as temp_dir:
        input_file = os.path.join(temp_dir, "benchmark_input.edi")
        generate_edi_data(input_file, RECORD_COUNT)

        # Mock settings and dependencies
        settings = {
            "as400_username": "mock_user",
            "as400_password": "mock_password",
            "as400_address": "localhost",
            "odbc_driver": "Mock Driver",
        }
        parameters = {}
        upc_lookup = {}

        # Mock query_runner to prevent DB connection attempts
        with patch("query_runner.query_runner") as mock_qr:
            # Mock the instance returned by the constructor
            mock_qr.return_value.run_arbitrary_query.return_value = []

            for module_name in CONVERTERS:
                try:
                    module = importlib.import_module(module_name)

                    # Try standard entry point first, then legacy edi_tweak
                    func = getattr(module, "edi_convert", None)
                    if not func:
                        func = getattr(module, "edi_tweak", None)

                    if not func:
                        print(f"{module_name:<25} | {'SKIPPED (no entry point)':<25}")
                        continue

                    times = []
                    for i in range(ITERATIONS):
                        output_base = os.path.join(
                            temp_dir, f"output_{module_name}_{i}"
                        )

                        start_time = time.perf_counter()
                        func(input_file, output_base, settings, parameters, upc_lookup)
                        end_time = time.perf_counter()
                        times.append(end_time - start_time)

                    avg_time = sum(times) / len(times)
                    rate = RECORD_COUNT / avg_time

                    print(f"{module_name:<25} | {avg_time:<12.4f} | {rate:<12.2f}")

                except ImportError:
                    print(f"{module_name:<25} | {'NOT FOUND':<25}")
                except Exception as e:
                    print(f"{module_name:<25} | {'ERROR':<12} | {str(e)}")


if __name__ == "__main__":
    run_benchmark()
