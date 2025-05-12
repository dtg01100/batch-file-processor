import csv
import decimal
from datetime import datetime, timedelta

from dateutil import parser

import utils
from query_runner import query_runner


class CustomerLookupError(Exception):
    pass

def edi_convert(edi_process, output_filename, settings_dict, parameters_dict, upc_dict):
    def convert_to_price(value):
        return (
            (value[:-2].lstrip("0") if not value[:-2].lstrip("0") == "" else "0")
            + "."
            + value[-2:]
        )

    def prettify_dates(date_string, offset=0, adj_offset=0):
        try:
            date_column_value = date_string
            stripped_date_value = str(date_column_value).strip()
            calculated_date_string = (
                str(int(stripped_date_value[0]) + 19) + stripped_date_value[1:]
            )
            parsed_date_string = parser.isoparse(calculated_date_string).date()
            corrected_date_string = parsed_date_string + timedelta(days=int(offset) + adj_offset)
            formatted_date_string = str(datetime.strftime(corrected_date_string, "%m/%d/%y"))
        except Exception:
            formatted_date_string = "Not Available"
        return formatted_date_string

    with open(edi_process, encoding="utf-8") as work_file:  # open input file
        work_file_lined = [n for n in work_file.readlines()]  # make list of lines
        with open(
            output_filename + ".csv", "w", newline="\n", encoding="utf-8"
        ) as f:  # open work file, overwriting old file
            csv_file = csv.writer(f, dialect="unix")
            query_object = query_runner(
                settings_dict["as400_username"],
                settings_dict["as400_password"],
                settings_dict["as400_address"],
                f"{settings_dict['odbc_driver']}",
            )

            # build header

            header_a_record = utils.capture_records(work_file_lined[0])

            header_fields = query_object.run_arbitrary_query(
                f"""
    SELECT TRIM(dsadrep.adbbtx) AS "Salesperson Name",
        ohhst.btcfdt AS "Invoice Date",
        TRIM(ohhst.btfdtx) AS "Terms Code",
        dsagrep.agrrnb AS "Terms Duration",
        dsabrep.abbvst AS "Customer Status",
        dsabrep.ababnb AS "Customer Number",
        TRIM(dsabrep.abaatx) AS "Customer Name",
        TRIM(dsabrep.ababtx) AS "Customer Address",
        TRIM(dsabrep.abaetx) AS "Customer Town",
        TRIM(dsabrep.abaftx) AS "Customer State",
        TRIM(dsabrep.abagtx) AS "Customer Zip",
        CONCAT(dsabrep.abadnb, dsabrep.abaenb) AS "Customer Phone",
        TRIM(cvgrrep.grm9xt) AS "Customer Email",
        TRIM(cvgrrep.grnaxt) AS "Customer Email 2",
        dsabrep_corp.abbvst AS "Corporate Customer Status",
        dsabrep_corp.ababnb AS "Corporate Customer Number",
        TRIM(dsabrep_corp.abaatx) AS "Corporate Customer Name",
        TRIM(dsabrep_corp.ababtx) AS "Corporate Customer Address",
        TRIM(dsabrep_corp.abaetx) AS "Corporate Customer Town",
        TRIM(dsabrep_corp.abaftx) AS "Corporate Customer State",
        TRIM(dsabrep_corp.abagtx) AS "Corporate Customer Zip",
        CONCAT(dsabrep_corp.abadnb, dsabrep.abaenb) AS "Corporate Customer Phone",
        TRIM(cvgrrep_corp.grm9xt) AS "Corporate Customer Email",
        TRIM(cvgrrep_corp.grnaxt) AS "Corporate Customer Email 2"
        FROM dacdata.ohhst ohhst
            INNER JOIN dacdata.dsabrep dsabrep
                ON ohhst.btabnb = dsabrep.ababnb
            left outer JOIN dacdata.cvgrrep cvgrrep
                ON dsabrep.ababnb = cvgrrep.grabnb
            INNER JOIN dacdata.dsadrep dsadrep
                ON dsabrep.abajcd = dsadrep.adaecd
                inner join dacdata.dsagrep dsagrep
                on ohhst.bta0cd = dsagrep.aga0cd
            LEFT outer JOIN dacdata.dsabrep dsabrep_corp
                ON dsabrep.abalnb = dsabrep_corp.ababnb
            LEFT outer JOIN dacdata.cvgrrep cvgrrep_corp
                ON dsabrep_corp.ababnb = cvgrrep_corp.grabnb
            LEFT outer JOIN dacdata.dsadrep dsadrep_corp
                ON dsabrep_corp.abajcd = dsadrep_corp.adaecd
        WHERE ohhst.bthhnb = {header_a_record['invoice_number'].lstrip("0")}
            """
            )

            # print(header_fields[0])

            header_fields_list = [
                "Salesperson_Name",
                "Invoice_Date",
                "Terms_Code",
                "Terms_Duration",
                "Customer_Status",
                "Customer_Number",
                "Customer_Name",
                "Customer_Address",
                "Customer_Town",
                "Customer_State",
                "Customer_Zip",
                "Customer_Phone",
                "Customer_Email",
                "Customer_Email_2",
                "Corporate_Customer_Status",
                "Corporate_Customer_Number",
                "Corporate_Customer_Name",
                "Corporate_Customer_Address",
                "Corporate_Customer_Town",
                "Corporate_Customer_State",
                "Corporate_Customer_Zip",
                "Corporate_Customer_Phone",
                "Corporate_Customer_Email",
                "Corporate_Customer_Email_2",
            ]

            if len(header_fields) == 0:
                raise CustomerLookupError(f"Cannot Find Order {header_a_record['invoice_number']} In History.")
            header_fields_dict = dict(zip(header_fields_list, header_fields[0]))
            if header_fields_dict["Corporate_Customer_Number"] is None:
                header_fields_dict["Corporate_Customer_Number"] = header_fields_dict['Customer_Number']
                header_fields_dict["Corporate_Customer_Name"] = header_fields_dict["Customer_Name"]
                header_fields_dict["Corporate_Customer_Address"] = header_fields_dict['Customer_Address']
                header_fields_dict["Corporate_Customer_Town"] = header_fields_dict['Customer_Town']
                header_fields_dict['Corporate_Customer_State'] = header_fields_dict['Customer_State']
                header_fields_dict['Corporate_Customer_Zip'] = header_fields_dict['Customer_Zip']

            csv_file.writerow(["Invoice Details"])
            csv_file.writerow([""])
            csv_file.writerow(
                ["Delivery Date", "Terms", "Invoice Number", "Due Date", "PO Number"]
            )
            csv_file.writerow(
                [
                    prettify_dates(header_fields_dict["Invoice_Date"]),
                    header_fields_dict["Terms_Code"],
                    header_a_record["invoice_number"],
                    prettify_dates(header_fields_dict["Invoice_Date"], header_fields_dict['Terms_Duration'], -1),
                ]
            )
            if header_fields_dict["Corporate_Customer_Number"] is not None:
                bill_to_segment = [
                    str(header_fields_dict['Corporate_Customer_Number']) + "\n" + \
                    header_fields_dict['Corporate_Customer_Name'] + "\n" + \
                    header_fields_dict['Corporate_Customer_Address'] + "\n" + \
                    header_fields_dict['Corporate_Customer_Town'] + ", " + header_fields_dict['Corporate_Customer_State'] + ", " + header_fields_dict['Corporate_Customer_Zip'] + ", " + "\n" + \
                "US",
                ]
            else:
                bill_to_segment = [
                    str(header_fields_dict['Customer_Number']) + "\n" + \
                    header_fields_dict['Customer_Name'] + "\n" + \
                    header_fields_dict['Customer_Address'] + "\n" + \
                    header_fields_dict['Customer_Town'] + ", " + header_fields_dict['Customer_State'] + ", " + header_fields_dict['Customer_Zip'] + ", " + "\n" + \
                    "US",
                ]
            csv_file.writerow(
                ["Ship To:",
                str(header_fields_dict['Customer_Number']) + "\n" + \
                header_fields_dict['Customer_Name'] + "\n" + \
                header_fields_dict['Customer_Address'] + "\n" + \
                header_fields_dict['Customer_Town'] + ", " + header_fields_dict['Customer_State'] + ", " + header_fields_dict['Customer_Zip'] + ", " + "\n" + \
                "US",
                "Bill To:"] + bill_to_segment
            )
            csv_file.writerow([""])
            csv_file.writerow(["Description", "UPC #", "Quantity", "UOM", "Price", "Amount"])

            uom_lookup_list = query_object.run_arbitrary_query(f"""
            select distinct bubacd as itemno, bus3qt as uom_mult, buhxtx as uom_code from dacdata.odhst odhst
            where odhst.buhhnb = {header_a_record['invoice_number']}
            """)

            def get_uom(item_number, packsize):
                stage_1_list = []
                stage_2_list = []
                for entry in uom_lookup_list:
                    if int(entry[0]) == int(item_number):
                        stage_1_list.append(entry)
                for entry in stage_1_list:
                    try:
                        if int(entry[1]) == int(packsize):
                            stage_2_list.append(entry)
                    except:
                        stage_2_list.append(entry)
                        break
                try:
                    retval = stage_2_list[0][2]
                except IndexError:
                    retval = '?'
                return(retval)

            def convert_to_item_total(unit_cost, qty):
                if qty.startswith('-'):
                    wrkqty = int(qty[1:])
                    wrkqtyint = wrkqty - (wrkqty * 2)
                else:
                    try:
                        wrkqtyint = int(qty)
                    except ValueError:
                        wrkqtyint = 0
                try:
                    item_total = decimal.Decimal(convert_to_price(unit_cost)) * wrkqtyint
                except ValueError:
                    item_total = decimal.Decimal()
                except decimal.InvalidOperation:
                    item_total = decimal.Decimal()
                return item_total, wrkqtyint

            def generate_full_upc(input_upc):
                input_upc = input_upc.strip()
                upc_string = ""
                blank_upc = False
                try:
                    _ = int(input_upc)
                except ValueError:
                    blank_upc = True

                if blank_upc is False:
                    proposed_upc = input_upc
                    if len(str(proposed_upc)) == 11:
                        upc_string = str(proposed_upc) + str(utils.calc_check_digit(proposed_upc))
                    else:
                        if len(str(proposed_upc)) == 8:
                            upc_string = str(utils.convert_UPCE_to_UPCA(proposed_upc))
                return upc_string

            for line_num, line in enumerate(
                work_file_lined
            ):  # iterate over work file contents
                input_edi_dict = utils.capture_records(line)
                if input_edi_dict is not None:
                    if input_edi_dict['record_type'] == 'B':
                        total_price, qtyint = convert_to_item_total(input_edi_dict['unit_cost'], input_edi_dict['qty_of_units'])
                        csv_file.writerow([
                            input_edi_dict['description'],
                            generate_full_upc(input_edi_dict['upc_number']),
                            qtyint,
                            get_uom(input_edi_dict['vendor_item'], input_edi_dict['unit_multiplier']),
                            "$"+str(convert_to_price(input_edi_dict['unit_cost'])),
                            "$"+str(total_price)
                        ])
                    if input_edi_dict['record_type'] == 'C':
                        csv_file.writerow([
                            input_edi_dict['description'],
                            '000000000000',
                            1,
                            'EA',
                            "$"+str(convert_to_price(input_edi_dict['amount'])),
                            "$"+str(convert_to_price(input_edi_dict['amount']))
                        ])
            csv_file.writerow(["","","","","Total:","$"+str(convert_to_price(header_a_record['invoice_total']).lstrip("0"))])
    return(output_filename + ".csv")
