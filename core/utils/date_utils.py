from datetime import datetime, timedelta

from dateutil import parser


def dactime_from_datetime(date_time: datetime) -> str:
    dactime_date_century_digit = str(int(datetime.strftime(date_time, "%Y")[:2]) - 19)
    dactime_date = dactime_date_century_digit + str(
        datetime.strftime(date_time.date(), "%y%m%d")
    )
    return dactime_date


def datetime_from_dactime(dac_time: int) -> datetime:
    dac_time_int = int(dac_time)
    return datetime.strptime(str(dac_time_int + 19000000), "%Y%m%d")


def datetime_from_invtime(invtime: str) -> datetime:
    return datetime.strptime(invtime, "%m%d%y")


def dactime_from_invtime(inv_no: str):
    datetime_obj = datetime_from_invtime(inv_no)
    dactime = dactime_from_datetime(datetime_obj)
    return dactime


def prettify_dates(date_string: str, offset: int = 0, adj_offset: int = 0) -> str:
    """Format a date string to mm/dd/yy format.

    Args:
        date_string: The input date string to format.
        offset: Number of days to add to the parsed date.
        adj_offset: Additional adjustment offset in days.

    Returns:
        A formatted date string in mm/dd/yy format, or "Not Available" if parsing fails.
    """
    try:
        stripped_date_value = str(date_string).strip()
        calculated_date_string = (
            str(int(stripped_date_value[0]) + 19) + stripped_date_value[1:]
        )
        parsed_date_string = parser.isoparse(calculated_date_string).date()
        corrected_date_string = parsed_date_string + timedelta(
            days=int(offset) + adj_offset
        )
        formatted_date_string = corrected_date_string.strftime("%m/%d/%y")
    except Exception:
        formatted_date_string = "Not Available"
    return formatted_date_string
