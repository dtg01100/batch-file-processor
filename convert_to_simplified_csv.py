import line_from_mtc_edi_to_dict
import csv
import upc_e_to_upc_a


class CustomerLookupError(Exception):
    pass

def edi_convert(edi_process, output_filename):

    def convert_to_price(value):
        return (
            (value[:-2].lstrip("0") if not value[:-2].lstrip("0") == "" else "0")
            + "."
            + value[-2:]
        )

    with open(edi_process) as work_file:  # open input file
        work_file_lined = [n for n in work_file.readlines()]  # make list of lines
        f = open(
            output_filename, "w", newline=""
        )  # open work file, overwriting old file
        csv_file = csv.writer(f, dialect="excel", lineterminator="\r\n")

        def qty_to_int(qty):
            if qty.startswith('-'):
                wrkqty = int(qty[1:])
                wrkqtyint = wrkqty - (wrkqty * 2)
            else:
                try:
                    wrkqtyint = int(qty)
                except ValueError:
                    wrkqtyint = 0
            return wrkqtyint

        for line_num, line in enumerate(
            work_file_lined
        ):  # iterate over work file contents
            input_edi_dict = line_from_mtc_edi_to_dict.capture_records(line)
            if input_edi_dict is not None:
                if input_edi_dict['record_type'] == 'B':
                    csv_file.writerow([
                        input_edi_dict['upc_number'],
                        qty_to_int(input_edi_dict['qty_of_units']),
                        convert_to_price(input_edi_dict['unit_cost'])
                    ])
        f.close()  # close output file
    return(output_filename)
