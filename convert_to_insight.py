import line_from_mtc_edi_to_dict


def edi_convert(edi_process, output_filename):
    work_file = open(edi_process)  # open input file
    f = open(output_filename, 'w')  # open work file, overwriting old file

    for line in work_file.readlines():
        if line.startswith("A"):
            f.write((line + "\r\n"))

        if line.startswith("B"):
            try:
                records = line_from_mtc_edi_to_dict.capture_records(line)
            except Exception:
                raise Exception("Not An EDI")

            unit_cost_with_decimal = records['unit_cost'][:-2] + "." + records['unit_cost'][-2:]
            suggested_retail_price_with_decimal = records['suggested_retail_price'][:-2] + \
                "." + records['suggested_retail_price'][-2:]

            f.write(records['record_type'] + records['upc_number'] + "  " +
                    records['description'] + records['vendor_item'][-5:] +
                    unit_cost_with_decimal + "  " +
                    records['unit_multiplier'] + records['qty_of_units'] + suggested_retail_price_with_decimal + "\r\n")

    f.close()  # close output file
