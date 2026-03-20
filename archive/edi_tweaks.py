"""EDI tweaks module for processing EDI files.

This module provides EDI file processing functionality including:
- PO number fetching
- C-record generation for split sales tax
- Various EDI record transformations

The module uses the refactored classes from core.edi.
"""

import os
import time
from datetime import datetime, timedelta
from decimal import Decimal

from core import utils
from core.database import query_runner
from core.edi.c_rec_generator import CRecGenerator
from core.edi.po_fetcher import POFetcher
from core.structured_logging import (
    StructuredLogger,
    get_logger,
    get_or_create_correlation_id,
)

logger = get_logger(__name__)


def _create_query_runner_adapter(settings_dict: dict):
    """Create an adapter that wraps legacy query_runner.

    This function creates a query runner from settings and wraps it
    with an adapter that implements the QueryRunnerProtocol.

    Args:
        settings_dict: Dictionary containing database connection settings

    Returns:
        Object implementing QueryRunnerProtocol
    """
    legacy_runner = query_runner(
        settings_dict["as400_username"],
        settings_dict["as400_password"],
        settings_dict["as400_address"],
        f"{settings_dict['odbc_driver']}",
    )

    class QueryRunnerAdapter:
        """Adapter wrapping legacy query_runner for protocol compliance."""

        def __init__(self, runner):
            self._runner = runner

        def run_query(self, query: str, params: tuple = None) -> list:
            # Legacy runner returns list of tuples
            return self._runner.run_arbitrary_query(query, params)

    return QueryRunnerAdapter(legacy_runner)


def edi_tweak(
    edi_process,
    output_filename,
    settings_dict,
    parameters_dict,
    upc_dict,
):
    """Apply EDI tweaks to process an EDI file.

    This function processes an EDI file, applying various transformations
    including date offsetting, UPC calculations, and C-record generation.

    Args:
        edi_process: Path to input EDI file
        output_filename: Path to output file
        settings_dict: Dictionary containing database and app settings
        parameters_dict: Dictionary containing processing parameters
        upc_dict: Dictionary containing UPC mappings

    Returns:
        Path to the output file
    """
    correlation_id = get_or_create_correlation_id()
    start_time = time.perf_counter()

    # Log entry with sanitized parameters
    StructuredLogger.log_entry(
        logger,
        "edi_tweak",
        __name__,
        args=(edi_process, output_filename),
        kwargs={
            "parameters_keys": list(parameters_dict.keys()),
            "upc_dict_size": len(upc_dict) if upc_dict else 0,
        },
    )

    StructuredLogger.log_debug(
        logger,
        "edi_tweak",
        __name__,
        f"Starting EDI tweak: {os.path.basename(edi_process)}",
        input_file=os.path.basename(edi_process),
        output_file=os.path.basename(output_filename),
        correlation_id=correlation_id,
    )

    try:
        # Parse and log enabled tweak parameters
        pad_arec = utils.normalize_bool(parameters_dict["pad_a_records"])
        arec_padding = parameters_dict["a_record_padding"]
        arec_padding_len = parameters_dict["a_record_padding_length"]
        append_arec = utils.normalize_bool(parameters_dict["append_a_records"])
        append_arec_text = parameters_dict["a_record_append_text"]
        invoice_date_custom_format = utils.normalize_bool(
            parameters_dict["invoice_date_custom_format"]
        )
        invoice_date_custom_format_string = parameters_dict[
            "invoice_date_custom_format_string"
        ]
        force_txt_file_ext = utils.normalize_bool(parameters_dict["force_txt_file_ext"])
        calc_upc = utils.normalize_bool(parameters_dict["calculate_upc_check_digit"])
        invoice_date_offset = parameters_dict.get("invoice_date_offset")
        invoice_date_offset = (
            int(invoice_date_offset) if invoice_date_offset is not None else 0
        )
        retail_uom = utils.normalize_bool(parameters_dict["retail_uom"])
        override_upc = utils.normalize_bool(parameters_dict["override_upc_bool"])
        override_upc_level = parameters_dict["override_upc_level"]
        override_upc_category_filter = parameters_dict["override_upc_category_filter"]
        split_prepaid_sales_tax_crec = utils.normalize_bool(
            parameters_dict["split_prepaid_sales_tax_crec"]
        )

        # Log enabled tweaks as debug
        enabled_tweaks = []
        if pad_arec:
            enabled_tweaks.append("pad_a_records")
        if append_arec:
            enabled_tweaks.append("append_a_records")
        if invoice_date_offset != 0:
            enabled_tweaks.append(f"date_offset({invoice_date_offset})")
        if invoice_date_custom_format:
            enabled_tweaks.append("date_format")
        if force_txt_file_ext:
            enabled_tweaks.append("force_txt")
        if calc_upc:
            enabled_tweaks.append("calc_upc")
        if retail_uom:
            enabled_tweaks.append("retail_uom")
        if override_upc:
            enabled_tweaks.append("override_upc")
        if split_prepaid_sales_tax_crec:
            enabled_tweaks.append("split_tax")

        StructuredLogger.log_debug(
            logger,
            "edi_tweak",
            __name__,
            f"Enabled tweaks: {enabled_tweaks}",
            enabled_tweaks=enabled_tweaks,
            correlation_id=correlation_id,
        )

        # Safely convert upc_target_length to int, defaulting 0/None to 11
        val = parameters_dict.get("upc_target_length")
        upc_target_length = int(val) if val else 11

        upc_padding_pattern = parameters_dict.get("upc_padding_pattern", "           ")

        work_file = None
        read_attempt_counter = 1
        while work_file is None:
            try:
                work_file = open(edi_process)  # open work file, overwriting old file
            except Exception as error:
                if read_attempt_counter >= 5:
                    time.sleep(read_attempt_counter * read_attempt_counter)
                    read_attempt_counter += 1
                    logger.info("Retrying open %s", edi_process)
                else:
                    logger.error(
                        "Error opening file for read %s: %s",
                        edi_process,
                        error,
                        exc_info=True,
                    )
                    raise

        # Log file read completion
        work_file_lined = [n for n in work_file.readlines()]  # make list of lines
        StructuredLogger.log_debug(
            logger,
            "edi_tweak",
            __name__,
            f"Read {len(work_file_lined)} lines from EDI file",
            line_count=len(work_file_lined),
            correlation_id=correlation_id,
        )

        if force_txt_file_ext:
            output_filename = output_filename + ".txt"
            StructuredLogger.log_debug(
                logger,
                "edi_tweak",
                __name__,
                f"Forced .txt extension: {output_filename}",
                output_file=output_filename,
                correlation_id=correlation_id,
            )

        f = None

        write_attempt_counter = 1
        while f is None:
            try:
                f = open(
                    output_filename, "w", newline="\r\n"
                )  # open work file, overwriting old file
            except Exception as error:
                if write_attempt_counter >= 5:
                    time.sleep(write_attempt_counter * write_attempt_counter)
                    write_attempt_counter += 1
                    logger.info("Retrying open %s", output_filename)
                else:
                    logger.error(
                        "Error opening file for write %s: %s",
                        output_filename,
                        error,
                        exc_info=True,
                    )
                    raise

        # Create query runner adapter for modern classes
        query_adapter = _create_query_runner_adapter(settings_dict)

        # Use modern classes directly
        crec_appender = CRecGenerator(query_adapter)
        po_fetcher = POFetcher(query_adapter)

        records_processed = 0
        a_records = 0
        b_records = 0
        c_records = 0

        for line_num, line in enumerate(
            work_file_lined
        ):  # iterate over work file contents
            input_edi_dict = utils.capture_records(line)
            writeable_line = line

            # Log intermediate progress every 100 records
            if line_num > 0 and line_num % 100 == 0:
                StructuredLogger.log_debug(
                    logger,
                    "edi_tweak",
                    __name__,
                    f"Processing: {line_num}/{len(work_file_lined)} lines",
                    progress={"current": line_num, "total": len(work_file_lined)},
                    correlation_id=correlation_id,
                )

            if writeable_line.startswith("A"):
                a_records += 1
                a_rec_edi_dict = input_edi_dict
                invoice_num = a_rec_edi_dict["invoice_number"]
                crec_appender.set_invoice_number(int(invoice_num))

                # Date offset transformation
                if invoice_date_offset != 0:
                    invoice_date_string = a_rec_edi_dict["invoice_date"]
                    if not invoice_date_string == "000000":
                        invoice_date = datetime.strptime(invoice_date_string, "%m%d%y")
                        offset_invoice_date = invoice_date + timedelta(
                            days=invoice_date_offset
                        )
                        a_rec_edi_dict["invoice_date"] = datetime.strftime(
                            offset_invoice_date, "%m%d%y"
                        )
                        StructuredLogger.log_intermediate(
                            logger,
                            "edi_tweak",
                            __name__,
                            "date_offset",
                            {
                                "invoice": invoice_num,
                                "original_date": invoice_date_string,
                                "offset_days": invoice_date_offset,
                            },
                            "applied",
                        )

                # Custom date format
                if invoice_date_custom_format:
                    invoice_date_string = a_rec_edi_dict["invoice_date"]
                    try:
                        invoice_date = datetime.strptime(invoice_date_string, "%m%d%y")
                        a_rec_edi_dict["invoice_date"] = datetime.strftime(
                            invoice_date, invoice_date_custom_format_string
                        )
                    except ValueError:
                        a_rec_edi_dict["invoice_date"] = "ERROR"
                        StructuredLogger.log_debug(
                            logger,
                            "edi_tweak",
                            __name__,
                            f"Date format error for invoice {invoice_num}",
                            invoice=invoice_num,
                            decision="error",
                            correlation_id=correlation_id,
                        )

                # A record padding
                if pad_arec:
                    padding = arec_padding
                    fill = " "
                    align = "<"
                    width = arec_padding_len
                    a_rec_edi_dict["cust_vendor"] = f"{padding:{fill}{align}{width}}"
                    StructuredLogger.log_intermediate(
                        logger,
                        "edi_tweak",
                        __name__,
                        "pad_a_record",
                        {"invoice": invoice_num},
                        "applied",
                    )

                a_rec_line_builder = [
                    a_rec_edi_dict["record_type"],
                    a_rec_edi_dict["cust_vendor"],
                    a_rec_edi_dict["invoice_number"],
                    a_rec_edi_dict["invoice_date"],
                    a_rec_edi_dict["invoice_total"],
                ]

                # Append PO number to A record
                if append_arec:
                    append_text = append_arec_text
                    if "%po_str%" in append_text:
                        po_number = po_fetcher.fetch_po_number(
                            a_rec_edi_dict["invoice_number"]
                        )
                        append_text = append_text.replace("%po_str%", po_number)
                        StructuredLogger.log_intermediate(
                            logger,
                            "edi_tweak",
                            __name__,
                            "append_po",
                            {"invoice": invoice_num, "po": po_number},
                            "fetched",
                        )
                    a_rec_line_builder.append(append_text)
                a_rec_line_builder.append("\n")
                writeable_line = "".join(a_rec_line_builder)
                f.write(writeable_line)

            if writeable_line.startswith("B"):
                b_records += 1
                b_rec_edi_dict = input_edi_dict

                # UPC override transformation
                if override_upc:
                    vendor_item = b_rec_edi_dict["vendor_item"].strip()
                    try:
                        category_filter = override_upc_category_filter.strip()
                        if category_filter == "" or category_filter == "ALL":
                            b_rec_edi_dict["upc_number"] = upc_dict[int(vendor_item)][
                                override_upc_level
                            ]
                            StructuredLogger.log_intermediate(
                                logger,
                                "edi_tweak",
                                __name__,
                                "override_upc",
                                {"vendor_item": vendor_item},
                                "applied",
                            )
                        else:
                            if upc_dict[int(vendor_item)][0] in category_filter.split(
                                ","
                            ):
                                b_rec_edi_dict["upc_number"] = upc_dict[
                                    int(vendor_item)
                                ][override_upc_level]
                                StructuredLogger.log_intermediate(
                                    logger,
                                    "edi_tweak",
                                    __name__,
                                    "override_upc",
                                    {"vendor_item": vendor_item},
                                    "applied_filtered",
                                )
                    except KeyError:
                        b_rec_edi_dict["upc_number"] = ""
                        StructuredLogger.log_debug(
                            logger,
                            "edi_tweak",
                            __name__,
                            f"UPC override not found for vendor item: {vendor_item}",
                            vendor_item=vendor_item,
                            decision="not_found",
                            correlation_id=correlation_id,
                        )

                # Retail UOM transformation
                if retail_uom:
                    edi_line_pass = False
                    try:
                        int(b_rec_edi_dict["vendor_item"].strip())
                        float(b_rec_edi_dict["unit_cost"].strip())
                        test_unit_multiplier = int(
                            b_rec_edi_dict["unit_multiplier"].strip()
                        )
                        if test_unit_multiplier == 0:
                            raise ValueError
                        int(b_rec_edi_dict["qty_of_units"].strip())
                        edi_line_pass = True
                    except Exception:
                        logger.debug(
                            "Cannot parse B record field, skipping: %s",
                            b_rec_edi_dict.get("vendor_item", "unknown"),
                        )
                    if edi_line_pass:
                        # Apply padding/truncating to whatever UPC is already in
                        # the field
                        try:
                            fill_char = (
                                upc_padding_pattern[0] if upc_padding_pattern else " "
                            )
                            current_upc = b_rec_edi_dict["upc_number"].strip()[
                                :upc_target_length
                            ]
                            b_rec_edi_dict["upc_number"] = current_upc.rjust(
                                upc_target_length, fill_char
                            )
                        except (AttributeError, TypeError):
                            # Fallback: use padding pattern if UPC is
                            # empty/invalid
                            b_rec_edi_dict["upc_number"] = upc_padding_pattern[
                                :upc_target_length
                            ]
                        try:
                            b_rec_edi_dict["unit_cost"] = (
                                str(
                                    Decimal(
                                        (
                                            Decimal(b_rec_edi_dict["unit_cost"].strip())
                                            / 100
                                        )
                                        / Decimal(
                                            b_rec_edi_dict["unit_multiplier"].strip()
                                        )
                                    ).quantize(Decimal(".01"))
                                )
                                .replace(".", "")[-6:]
                                .rjust(6, "0")
                            )
                            b_rec_edi_dict["qty_of_units"] = str(
                                int(b_rec_edi_dict["unit_multiplier"].strip())
                                * int(b_rec_edi_dict["qty_of_units"].strip())
                            ).rjust(5, "0")
                            b_rec_edi_dict["unit_multiplier"] = "000001"
                            StructuredLogger.log_intermediate(
                                logger,
                                "edi_tweak",
                                __name__,
                                "retail_uom",
                                {"vendor_item": b_rec_edi_dict["vendor_item"].strip()},
                                "applied",
                            )
                        except Exception as error:
                            logger.debug(
                                "Retail UOM error: %s",
                                error,
                            )

                # UPC check digit calculation
                if calc_upc:
                    blank_upc = False
                    try:
                        _ = int(b_rec_edi_dict["upc_number"].rstrip())
                    except ValueError:
                        blank_upc = True

                    if blank_upc is False:
                        proposed_upc = b_rec_edi_dict["upc_number"].strip()
                        proposed_len = len(str(proposed_upc))
                        if proposed_len == upc_target_length:
                            # Exact match, is valid
                            pass
                        elif proposed_len == 12 and upc_target_length == 13:
                            # Pad a 12-char UPC with check digit to length 13.
                            fill_char = (
                                upc_padding_pattern[0] if upc_padding_pattern else " "
                            )
                            b_rec_edi_dict["upc_number"] = str(proposed_upc).rjust(
                                upc_target_length, fill_char
                            )
                            StructuredLogger.log_intermediate(
                                logger,
                                "edi_tweak",
                                __name__,
                                "pad_upc",
                                {"upc": proposed_upc, "target": upc_target_length},
                                "padded",
                            )
                        elif proposed_len == 11:
                            # Add check digit to 11-char base UPC
                            check_digit = utils.calc_check_digit(proposed_upc)
                            b_rec_edi_dict["upc_number"] = str(proposed_upc) + str(
                                check_digit
                            )
                            StructuredLogger.log_intermediate(
                                logger,
                                "edi_tweak",
                                __name__,
                                "calc_upc_check_digit",
                                {"upc": proposed_upc},
                                "added",
                            )
                        elif proposed_len == 8:
                            # Convert UPC-E to UPCA
                            b_rec_edi_dict["upc_number"] = str(
                                utils.convert_UPCE_to_UPCA(proposed_upc)
                            )
                            StructuredLogger.log_intermediate(
                                logger,
                                "edi_tweak",
                                __name__,
                                "convert_upce_to_upca",
                                {"upce": proposed_upc},
                                "converted",
                            )
                    else:
                        b_rec_edi_dict["upc_number"] = upc_padding_pattern[
                            :upc_target_length
                        ]

                # Determine parent-item handling AFTER UPC and numeric tweaks.
                projected_b_line = "".join(
                    (
                        b_rec_edi_dict["record_type"],
                        b_rec_edi_dict["upc_number"],
                        b_rec_edi_dict["description"],
                        b_rec_edi_dict["vendor_item"],
                        b_rec_edi_dict["unit_cost"],
                        b_rec_edi_dict["combo_code"],
                        b_rec_edi_dict["unit_multiplier"],
                        b_rec_edi_dict["qty_of_units"],
                        b_rec_edi_dict["suggested_retail_price"],
                        b_rec_edi_dict["price_multi_pack"],
                        b_rec_edi_dict["parent_item_number"],
                    )
                )
                if len(projected_b_line) < 76:
                    b_rec_edi_dict["parent_item_number"] = ""
                    StructuredLogger.log_intermediate(
                        logger,
                        "edi_tweak",
                        __name__,
                        "parent_item",
                        {},
                        "cleared_short_record",
                    )

                digits_fields = [
                    "unit_cost",
                    "unit_multiplier",
                    "qty_of_units",
                    "suggested_retail_price",
                ]

                for field in digits_fields:
                    tempfield = b_rec_edi_dict[field].replace("-", "")
                    if len(tempfield) != len(b_rec_edi_dict[field]):
                        b_rec_edi_dict[field] = "-" + tempfield

                writeable_line = "".join(
                    (
                        b_rec_edi_dict["record_type"],
                        b_rec_edi_dict["upc_number"],
                        b_rec_edi_dict["description"],
                        b_rec_edi_dict["vendor_item"],
                        b_rec_edi_dict["unit_cost"],
                        b_rec_edi_dict["combo_code"],
                        b_rec_edi_dict["unit_multiplier"],
                        b_rec_edi_dict["qty_of_units"],
                        b_rec_edi_dict["suggested_retail_price"],
                        b_rec_edi_dict["price_multi_pack"],
                        b_rec_edi_dict["parent_item_number"],
                        "\n",
                    )
                )
                f.write(writeable_line)

            if writeable_line.startswith("C"):
                c_records += 1
                if (
                    split_prepaid_sales_tax_crec
                    and crec_appender.unappended_records
                    and writeable_line.startswith("CTABSales Tax")
                ):
                    StructuredLogger.log_intermediate(
                        logger,
                        "edi_tweak",
                        __name__,
                        "split_tax_crec",
                        {},
                        "generating",
                    )
                    crec_appender.fetch_splitted_sales_tax_totals(f)
                else:
                    f.write(writeable_line)

            records_processed += 1

        f.close()  # close output file

        # Log final statistics
        duration_ms = (time.perf_counter() - start_time) * 1000

        StructuredLogger.log_debug(
            logger,
            "edi_tweak",
            __name__,
            f"EDI tweak completed: {records_processed} records processed",
            records={
                "total": records_processed,
                "a_records": a_records,
                "b_records": b_records,
                "c_records": c_records,
            },
            duration_ms=round(duration_ms, 2),
            correlation_id=correlation_id,
        )

        # Log exit
        StructuredLogger.log_exit(
            logger,
            "edi_tweak",
            __name__,
            output_filename,
            duration_ms,
        )

        return output_filename

    except Exception as e:
        duration_ms = (time.perf_counter() - start_time) * 1000
        StructuredLogger.log_error(
            logger,
            "edi_tweak",
            __name__,
            e,
            {
                "input_file": edi_process,
                "output_file": output_filename,
            },
            duration_ms,
        )
        raise
