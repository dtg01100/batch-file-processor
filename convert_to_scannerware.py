from datetime import datetime, timedelta

import line_from_mtc_edi_to_dict


def edi_convert(edi_process, output_filename, settings_dict, parameters_dict, upc_lookup):

    arec_padding = parameters_dict['a_record_padding']
    append_arec = parameters_dict['append_a_records']
    append_arec_text = parameters_dict['a_record_append_text']
    force_txt_file_ext = parameters_dict['force_txt_file_ext']
    invoice_date_offset = parameters_dict['invoice_date_offset']

    with open(edi_process, encoding="utf-8") as work_file:  # open input file
        work_file_lined = [n for n in work_file.readlines()]  # make list of lines
    if force_txt_file_ext == "True":
        output_filename = output_filename + ".txt"
    with open(output_filename, 'wb') as f:  # open work file, overwriting old file
        for line_num, line in enumerate(work_file_lined):  # iterate over work file contents
            input_edi_dict = line_from_mtc_edi_to_dict.capture_records(line)
            writeable_line = line.strip("\r\n")
            line_builder_list = []
            if writeable_line.startswith("A"):
                line_builder_list.append(input_edi_dict['record_type'])
                line_builder_list.append(arec_padding.ljust(6))
                line_builder_list.append(input_edi_dict['invoice_number'][-7:])
                line_builder_list.append('   ')

                write_invoice_date = line_from_mtc_edi_to_dict.capture_records(writeable_line)['invoice_date']
                if invoice_date_offset != 0:
                    invoice_date_string = line_from_mtc_edi_to_dict.capture_records(writeable_line)['invoice_date']
                    if not invoice_date_string == '000000':
                        invoice_date = datetime.strptime(invoice_date_string, '%m%d%y')
                        offset_invoice_date = invoice_date + timedelta(days=invoice_date_offset)
                        write_invoice_date = datetime.strftime(offset_invoice_date, '%m%d%y')
                line_builder_list.append(write_invoice_date)
                line_builder_list.append(input_edi_dict['invoice_total'])
                if append_arec == "True":
                    line_builder_list.append(append_arec_text)

            if writeable_line.startswith("B"):
                line_builder_list.append(input_edi_dict['record_type'])
                line_builder_list.append(input_edi_dict['upc_number'].ljust(14))
                line_builder_list.append(input_edi_dict['description'][:25])
                line_builder_list.append(input_edi_dict['vendor_item'])
                line_builder_list.append(input_edi_dict['unit_cost'])
                line_builder_list.append('  ')
                line_builder_list.append(input_edi_dict['unit_multiplier'])
                line_builder_list.append(input_edi_dict['qty_of_units'])
                line_builder_list.append(input_edi_dict['suggested_retail_price'])
                line_builder_list.append('001')
                line_builder_list.append('       ')
            if writeable_line.startswith("C"):
                line_builder_list.append(input_edi_dict['record_type'])
                line_builder_list.append(input_edi_dict['description'].ljust(25))
                line_builder_list.append('   ')
                line_builder_list.append(input_edi_dict['amount'])
            writeable_line = "".join(line_builder_list)
            f.write((writeable_line + '\r\n').encode())

    return output_filename


if __name__ == "__main__":
    import os
    import tempfile
    with tempfile.TemporaryDirectory() as workdir:
        infile_path = os.path.abspath(input("input file path: "))
        outfile_path = os.path.join(os.path.expanduser('~'), os.path.basename(infile_path))
        new_outfile = edi_convert(infile_path, outfile_path, "CAPCDY", "True", "123456", False, 0)
        with open(new_outfile, 'r', encoding="utf-8") as new_outfile_handle:
            for entry in new_outfile_handle.readlines():
                print(repr(entry))

