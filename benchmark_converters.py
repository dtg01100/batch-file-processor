import time
import os
import glob
import importlib
import tempfile
import shutil
import sys
import contextlib

# Ensure current directory is in path
sys.path.append(os.getcwd())


@contextlib.contextmanager
def suppress_stdout_stderr():
    """A context manager that redirects stdout and stderr to devnull"""
    with open(os.devnull, "w") as devnull:
        old_stdout = sys.stdout
        old_stderr = sys.stderr
        sys.stdout = devnull
        sys.stderr = devnull
        try:
            yield
        finally:
            sys.stdout = old_stdout
            sys.stderr = old_stderr


def generate_sample_edi(file_path, num_invoices=100, items_per_invoice=50):
    with open(file_path, "w") as f:
        for i in range(num_invoices):
            inv_num = f"{i:06d}"
            # A record
            f.write(f"A000001INV{inv_num}011221251000012345\n")
            for j in range(items_per_invoice):
                # B record
                f.write(
                    f"B012345678901Product Description {j:06d}1234567890100001000100050000\n"
                )
            # C record
            f.write(f"C00100000123\n")


def benchmark():
    # Setup
    converters = glob.glob("convert_to_*.py")
    converters = [os.path.basename(c).replace(".py", "") for c in converters]

    # Filter out edi_tweaks as it's not a standard format converter usually
    if "convert_to_edi_tweaks" in converters:
        converters.remove("convert_to_edi_tweaks")

    print(f"Found {len(converters)} converters: {', '.join(converters)}")

    with tempfile.TemporaryDirectory() as temp_dir:
        input_file = os.path.join(temp_dir, "benchmark_input.edi")
        print("Generating sample EDI file (100 invoices, 100 items each)...")
        generate_sample_edi(input_file, num_invoices=100, items_per_invoice=100)
        file_size = os.path.getsize(input_file) / (1024 * 1024)
        print(f"Sample file size: {file_size:.2f} MB")

        results = {}

        # Mock settings/params
        settings = {
            "as400_username": "user",
            "as400_password": "password",
            "as400_address": "localhost",
            "odbc_driver": "driver",
        }
        params = {
            "edi_format": "default",
            "include_headers": "True",
            "include_a_records": "True",
            "include_c_records": "True",
            # Estore params
            "estore_store_number": "001",
            "estore_Vendor_OId": "VENDOR",
            "estore_vendor_NameVendorOID": "VENDOR_OID",
            # Generic
            "rename_file": "",
            "split_edi": False,
            "process_edi": "True",
        }
        upc_lookup = {}

        print("\nRunning benchmarks (suppressing converter output)...")

        for conv_name in converters:
            output_file = os.path.join(temp_dir, f"output_{conv_name}")

            try:
                module = importlib.import_module(conv_name)
                if not hasattr(module, "edi_convert"):
                    print(f"Skipping {conv_name}: No edi_convert function")
                    continue

                start_time = time.time()
                try:
                    with suppress_stdout_stderr():
                        module.edi_convert(
                            input_file, output_file, settings, params, upc_lookup
                        )
                    end_time = time.time()
                    duration = end_time - start_time
                    results[conv_name] = duration
                    print(f"✓ {conv_name:<40} {duration:.4f}s")
                except Exception as e:
                    print(f"✗ {conv_name:<40} Failed: {str(e)}")
                    results[conv_name] = f"Error: {str(e)}"

            except Exception as e:
                print(f"✗ {conv_name:<40} Import failed: {str(e)}")

    print("\nBenchmark Results:")
    print("-" * 60)
    print(f"{'Converter':<40} | {'Time (s)':<15}")
    print("-" * 60)

    # Sort results by time (errors last)
    sorted_results = sorted(
        results.items(), key=lambda x: x[1] if isinstance(x[1], float) else 999999
    )

    for name, result in sorted_results:
        if isinstance(result, float):
            print(f"{name:<40} | {result:.4f}")
        else:
            print(f"{name:<40} | {result}")
    print("-" * 60)


if __name__ == "__main__":
    benchmark()
