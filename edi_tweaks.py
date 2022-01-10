import upc_e_to_upc_a
import line_from_mtc_edi_to_dict
from datetime import datetime, timedelta
from query_runner import query_runner



def edi_tweak(
    edi_process,
    output_filename,
    pad_arec,
    arec_padding,
    append_arec,
    append_arec_text,
    force_txt_file_ext,
    calc_upc,
    invoice_date_offset,
    retail_uom
):
    work_file = open(edi_process)  # open input file
    work_file_lined = [n for n in work_file.readlines()]  # make list of lines
    if force_txt_file_ext == "True":
        output_filename = output_filename + ".txt"
    f = open(output_filename, "wb")  # open work file, overwriting old file
    for line_num, line in enumerate(work_file_lined):  # iterate over work file contents
        input_edi_dict = line_from_mtc_edi_to_dict.capture_records(line)
        writeable_line = line
        if writeable_line.startswith("A"):
            if invoice_date_offset != 0:
                invoice_date_string = line_from_mtc_edi_to_dict.capture_records(
                    writeable_line
                )["invoice_date"]
                if not invoice_date_string == "000000":
                    invoice_date = datetime.strptime(invoice_date_string, "%m%d%y")
                    offset_invoice_date = invoice_date + timedelta(
                        days=invoice_date_offset
                    )
                    writeable_line = (
                        writeable_line[0:17]
                        + datetime.strftime(offset_invoice_date, "%m%d%y")
                        + writeable_line[23:]
                    )
            if pad_arec == "True":
                writeable_line = (
                    writeable_line[0:1] + arec_padding[0:6] + writeable_line[7:]
                )  # write "A" line
            if append_arec == "True":
                writeable_line = writeable_line.rstrip() + append_arec_text + "\n"
        if writeable_line.startswith("B"):
            b_rec_edi_dict = input_edi_dict
            if calc_upc == "True":
                blank_upc = False
                try:
                    _ = int(input_edi_dict["upc_number"].rstrip())
                except ValueError:
                    blank_upc = True

                if blank_upc is False:
                    proposed_upc = input_edi_dict["upc_number"].strip()
                    if len(str(proposed_upc)) == 11:
                        b_rec_edi_dict['upc_number'] = str(proposed_upc) + str(
                            upc_e_to_upc_a.calc_check_digit(proposed_upc)
                        )
                    else:
                        if len(str(proposed_upc)) == 8:
                            b_rec_edi_dict['upc_number'] = str(
                                upc_e_to_upc_a.convert_UPCE_to_UPCA(proposed_upc)
                            )
                else:
                    b_rec_edi_dict['upc_number'] = "            "
                # record_type=line[0],
                #       upc_number=line[1:12],
                #       description=line[12:37],
                #       vendor_item=line[37:43],
                #       unit_cost=line[43:49],
                #       combo_code=line[49:51],
                #       unit_multiplier=line[51:57],
                #       qty_of_units=line[57:62],
                #       suggested_retail_price=line[62:67]
            writeable_line = (
                b_rec_edi_dict["record_type"]
                + b_rec_edi_dict["upc_number"]
                + b_rec_edi_dict["description"]
                + b_rec_edi_dict["vendor_item"]
                + b_rec_edi_dict["unit_cost"]
                + b_rec_edi_dict["combo_code"]
                + b_rec_edi_dict["unit_multiplier"]
                + b_rec_edi_dict["qty_of_units"]
                + b_rec_edi_dict["suggested_retail_price"]
            )
        f.write(writeable_line.replace("\n", "\r\n").encode())
    else:
        f.write(chr(26).encode())

    f.close()  # close output file
    return output_filename
