import time
from io import StringIO

import utils

try:
    from edi_format_parser import EDIFormatParser

    HAS_FORMAT_PARSER = True
except ImportError:
    HAS_FORMAT_PARSER = False
    EDIFormatParser = None


def check(input_file, parser=None):
    if parser is None and HAS_FORMAT_PARSER and EDIFormatParser:
        try:
            parser = EDIFormatParser.get_default_parser()
        except Exception:
            pass

    line_number = 0
    file_to_test = None

    try:
        validator_open_attempts = 1
        while file_to_test is None:
            try:
                file_to_test = open(input_file)
            except Exception as error:
                if validator_open_attempts < 5:
                    time.sleep(validator_open_attempts * validator_open_attempts)
                    validator_open_attempts += 1
                    print(f"retrying open {input_file}")
                else:
                    print(f"error opening file for read {error}")
                    raise

        first_char = file_to_test.read(1)
        expected_start = "A"
        if parser and hasattr(parser, "validation_rules"):
            expected_start = parser.validation_rules.get("file_must_start_with", "A")

        if first_char != expected_start:
            file_to_test.close()
            return False, 1

        file_to_test.seek(0)

        allowed_types = ["A", "B", "C", ""]
        if parser and hasattr(parser, "validation_rules"):
            allowed_types = parser.validation_rules.get(
                "allowed_record_types", ["A", "B", "C"]
            ) + [""]

        b_record_lengths = [71, 77]
        if parser and hasattr(parser, "validation_rules"):
            b_record_lengths = parser.validation_rules.get("b_record_lengths", [71, 77])

        for line in file_to_test:
            line_number += 1
            if line[0] == "\x1a":
                continue
            if line[0] not in allowed_types:
                file_to_test.close()
                return False, line_number
            else:
                try:
                    if line[0] == "B":
                        if len(line) not in b_record_lengths:
                            file_to_test.close()
                            return False, line_number
                        _ = int(line[1:12])
                        if len(line) == 71 and line[51:67] != "                ":
                            file_to_test.close()
                            return False, line_number
                except ValueError:
                    if not line[1:12] == "           ":
                        file_to_test.close()
                        return False, line_number

        file_to_test.close()
        return True, line_number
    except Exception as eerror:
        print(eerror)
        if file_to_test is not None:
            file_to_test.close()
        return False, line_number


def report_edi_issues(input_file, parser=None):
    if parser is None and HAS_FORMAT_PARSER and EDIFormatParser:
        try:
            parser = EDIFormatParser.get_default_parser()
        except Exception:
            pass

    def _insert_description_and_number(issue_line):
        line_dict = utils.capture_records(issue_line, parser)
        if line_dict:
            in_memory_log.write(
                "Item description: " + line_dict.get("description", "") + "\r\n"
            )
            in_memory_log.write(
                "Item number: " + line_dict.get("vendor_item", "") + "\r\n\r\n"
            )

    in_memory_log = StringIO()
    line_number = 0
    has_errors = False
    has_minor_errors = False
    validator_open_attempts = 1
    input_file_handle = None
    while input_file_handle is None:
        try:
            input_file_handle = open(input_file)
        except Exception as error:
            if validator_open_attempts < 5:
                time.sleep(validator_open_attempts * validator_open_attempts)
                validator_open_attempts += 1
                print(f"retrying open {input_file}")
            else:
                print(f"error opening file for read {error}")
                raise

    # input_file_handle = open(input_file)
    check_pass, check_line_number = check(input_file, parser)
    if check_pass is True:
        for line in input_file_handle:
            line_number += 1
            try:
                if line[0] == "B":
                    proposed_upc = line[1:12]
                    if len(str(proposed_upc).strip()) == 8:
                        has_minor_errors = True
                        in_memory_log.write(
                            "Suppressed UPC in line " + str(line_number) + "\r\n"
                        )
                        in_memory_log.write("line is:\r\n")
                        in_memory_log.write(line + "\r\n")
                        _insert_description_and_number(line)
                    else:
                        if 11 > len(str(proposed_upc).strip()) > 0:
                            has_minor_errors = True
                            in_memory_log.write(
                                "Truncated UPC in line " + str(line_number) + "\r\n"
                            )
                            in_memory_log.write("line is:\r\n")
                            in_memory_log.write(line + "\r\n")
                            _insert_description_and_number(line)
                    if line[1:12] == "           ":
                        has_minor_errors = True
                        in_memory_log.write(
                            "Blank UPC in line " + str(line_number) + "\r\n"
                        )
                        in_memory_log.write("line is:\r\n")
                        in_memory_log.write(line + "\r\n")
                        _insert_description_and_number(line)
                    if len(line) == 71:
                        has_minor_errors = True
                        has_minor_errors = True
                        in_memory_log.write(
                            "Missing pricing information in line "
                            + str(line_number)
                            + ". Is this a sample?"
                            + "\r\n"
                        )
                        in_memory_log.write("line is:\r\n")
                        in_memory_log.write(line + "\r\n")
                        _insert_description_and_number(line)
            except Exception as error:
                has_errors = True
                in_memory_log.write(
                    "Validator produced error "
                    + str(error)
                    + " in line "
                    + str(line_number)
                    + "\r\n"
                )
                in_memory_log.write("line is:\r\n")
                in_memory_log.write(line + "\r\n")
                _insert_description_and_number(line)
    else:
        in_memory_log.write(
            "EDI check failed on line number: " + str(check_line_number) + "\r\n"
        )
        has_errors = True
    input_file_handle.close()
    return in_memory_log, has_errors, has_minor_errors
