import line_from_mtc_edi_to_dict
from query_runner import query_runner

def edi_convert(edi_process, output_filename, settings_dict):

    work_file = open(edi_process)  # open input file
    work_file_lined = [n for n in work_file.readlines()]  # make list of lines
    invoice_list = []

    for line_num, line in enumerate(work_file_lined):  # iterate over work file contents
        input_edi_dict = line_from_mtc_edi_to_dict.capture_records(line)
        if input_edi_dict['record_type'] == "A":
            invoice_list.append(input_edi_dict['invoice_number'])
