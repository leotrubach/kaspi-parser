import datetime
from decimal import Decimal


def parse_date(s) -> datetime.date:
    day, month, year = map(int, s.split("."))
    return datetime.date(year+2000, month, day)


def parse_amount(s) -> Decimal:
    normalized = s.replace(" ", "").replace(",", ".").split('₸')[0]
    return Decimal(normalized)
