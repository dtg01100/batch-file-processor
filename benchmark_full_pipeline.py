"""
Performance Benchmark Script for the Full Batch File Processor Pipeline.

This script benchmarks the end-to-end performance of the batch file processor
by simulating a full processing run including splitting, converting, tweaking,
and file naming using the EDIProcessor class.
"""

import importlib
import os
import sys
import tempfile
import time
from unittest.mock import patch, MagicMock

# Ensure project root is in path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from dispatch.edi_processor import EDIProcessor

# Benchmark configuration
RECORD_COUNT = 5000  # Number of B records
ITERATIONS = 3  # Number of runs for the full pipeline


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


def run_full_pipeline_benchmark():
    print(f"Starting full pipeline benchmark with {RECORD_COUNT} records per file...")
    print(f"{'Run':<5} | {'Time (s)':<12} | {'Rate (rec/s)':<12}")
    print("-" * 35)

    with tempfile.TemporaryDirectory() as temp_dir:
        input_file = os.path.join(temp_dir, "benchmark_input.edi")
        generate_edi_data(input_file, RECORD_COUNT)

        # Mock settings and parameters for the full pipeline
        settings = {
            "as400_username": "mock_user",
            "as400_password": "mock_password",
            "as400_address": "localhost",
            "odbc_driver": "Mock Driver",
        }
        parameters = {
            "convert_to_format": "CSV",
            "process_edi": "True",
            "tweak_edi": True,
            "split_edi": True,
            "rename_file": "output_%datetime%",
            "prepend_date_files": False,
        }
        upc_lookup = {}

        times = []

        # Mock query_runner to prevent DB connection attempts
        # and convert_to_edi_tweaks.edi_tweak which is called by EDITweaker
        with patch("query_runner.query_runner") as mock_qr, \
             patch("dispatch.edi_processor.convert_to_edi_tweaks.edi_tweak") as mock_edi_tweak, \
             patch("dispatch.edi_processor.utils.do_split_edi") as mock_do_split_edi, \
             patch("dispatch.edi_processor.importlib.import_module") as mock_import_module:

            mock_qr.return_value.run_arbitrary_query.return_value = []
            mock_edi_tweak.side_effect = lambda *args, **kwargs: args[1] # Return output_file
            
            # Simulate 3 split files
            mock_do_split_edi.side_effect = lambda input_file, scratch_folder, params: [
                (os.path.join(scratch_folder, "split_1.edi"), "", ""),
                (os.path.join(scratch_folder, "split_2.edi"), "", ""),
                (os.path.join(scratch_folder, "split_3.edi"), "", ""),
            ]
            
            # Mock importlib to return a mock converter module
            mock_converter_module = MagicMock()
            mock_converter_module.edi_convert.side_effect = lambda *args, **kwargs: args[1] # Return output_file
            mock_import_module.return_value = mock_converter_module

            for i in range(ITERATIONS):
                # Need a fresh scratch folder for each iteration to avoid file conflicts
                with tempfile.TemporaryDirectory() as iter_temp_dir:
                    # Regenerate input file for each iteration
                    iter_input_file = os.path.join(iter_temp_dir, "benchmark_input.edi")
                    generate_edi_data(iter_input_file, RECORD_COUNT)

                    start_time = time.perf_counter()
                    EDIProcessor.process_edi(
                        iter_input_file,
                        parameters,
                        settings,
                        upc_lookup,
                        iter_temp_dir,
                    )
                    end_time = time.perf_counter()
                    times.append(end_time - start_time)

                    avg_time = sum(times) / len(times)
                    rate = RECORD_COUNT / avg_time
                    print(f"{i+1:<5} | {times[-1]:<12.4f} | {rate:<12.2f}")

        overall_avg_time = sum(times) / len(times)
        overall_rate = RECORD_COUNT / overall_avg_time

        print("-" * 35)
        print(f"{'Overall Avg':<5} | {overall_avg_time:<12.4f} | {overall_rate:<12.2f}")


if __name__ == "__main__":
    run_full_pipeline_benchmark()
