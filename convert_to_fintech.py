import csv
from datetime import datetime

import utils

def edi_convert(edi_process, output_filename, settings_dict, parameters_dict, upc_lut):
    # save input parameters as variables

    invFetcher = utils.invFetcher

    fintech_division_id = parameters_dict['fintech_division_id']

    with open(edi_process, encoding="utf-8") as work_file:  # open input file
        work_file_lined = [n for n in work_file.readlines()]  # make list of lines
        with open(output_filename + ".csv", "w", newline="", encoding="utf-8") as f:  # open work file, overwriting old file
            csv_file = csv.writer(f, dialect="excel", lineterminator="\r\n", quoting=csv.QUOTE_ALL)

            csv_file.writerow([
                "Division_id",
                "invoice_number",
                "invoice_date",
                "Vendor_store_id",
                "quantity_shipped",
                "Quantity_uom",
                "item_number",
                "upc_pack",
                "upc_case",
                "product_description",
                "unit_price"
            ])

            arec_header = {}
            inv_fetcher = invFetcher(settings_dict)
            lineno = 0

            for line_num, line in enumerate(work_file_lined):  # iterate over work file contents
                input_edi_dict = utils.capture_records(line)
                if input_edi_dict is not None:
                    if input_edi_dict['record_type'] == "A":
                        arec_header = input_edi_dict
                        lineno = 0
                    if input_edi_dict['record_type'] == "B":
                        csv_file.writerow([
                            fintech_division_id,
                            int(arec_header['invoice_number']),
                            utils.datetime_from_invtime(arec_header['invoice_date']).strftime("%m/%d/%Y"),
                            inv_fetcher.fetch_cust_no(int(arec_header['invoice_number'])),
                            int(input_edi_dict['qty_of_units']),
                            inv_fetcher.fetch_uom_desc(input_edi_dict['vendor_item'], input_edi_dict['unit_multiplier'], lineno, int(arec_header['invoice_number'])),
                            input_edi_dict['vendor_item'],
                            upc_lut[int(input_edi_dict['vendor_item'])][1],
                            upc_lut[int(input_edi_dict['vendor_item'])][2],
                            input_edi_dict['description'],
                            utils.convert_to_price(input_edi_dict['unit_cost'])
                        ])
                        lineno += 1

        return output_filename + ".csv"
