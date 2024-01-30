from datetime import datetime


def dac_str_int_to_int(dacstr: str) -> int:
    if dacstr.strip() == "":
        return 0
    if dacstr.startswith('-'):
        return int(dacstr[1:]) - (int(dacstr[1:]) * 2)
    else:
        return int(dacstr)


def convert_to_price(value):
    return (value[:-2].lstrip("0") if not value[:-2].lstrip("0") == "" else "0") + "." + value[-2:]


def dactime_from_datetime(date_time: datetime) -> str:
    dactime_date_century_digit = str(int(datetime.strftime(date_time, "%Y")[:2]) - 19)
    dactime_date = dactime_date_century_digit + str(
        datetime.strftime(date_time.date(), "%y%m%d")
    )
    return dactime_date


def datetime_from_dactime(dac_time: int) -> datetime:
    dac_time_int = int(dac_time)
    return datetime.strptime(str(dac_time_int + 19000000), "%Y%m%d")


def datetime_from_invtime(invtime: int) -> datetime:
    return datetime.strptime(invtime, "%m%d%y")


def dac_str_int_to_int(dacstr: str) -> int:
    if dacstr.strip() == "":
        return 0
    if dacstr.startswith('-'):
        return int(dacstr[1:]) - (int(dacstr[1:]) * 2)
    else:
        return int(dacstr)
