import csv
import io
import re
from dataclasses import dataclass, field
from datetime import date
from decimal import Decimal

from .model import Transaction, money


class ParseError(Exception):
    def __init__(self, line: int, message: str):
        super().__init__(f"line {line}: {message}")
        self.line = line
        self.message = message


@dataclass
class ParseResult:
    transactions: list = field(default_factory=list)
    errors: list = field(default_factory=list)


_MONTHS = ["january", "february", "march", "april", "may", "june", "july",
           "august", "september", "october", "november", "december"]


def parse_date(text: str) -> date:
    s = text.strip()
    if m := re.fullmatch(r"(\d{4})-(\d{2})-(\d{2})", s):
        y, mo, d = map(int, m.groups())
    elif m := re.fullmatch(r"(\d{1,2})/(\d{1,2})/(\d{4})", s):
        d, mo, y = map(int, m.groups())
    elif m := re.fullmatch(r"([A-Za-z]+) (\d{1,2}), (\d{4})", s):
        name = m.group(1).lower()
        matches = [i for i, full in enumerate(_MONTHS, 1) if name in (full, full[:3])]
        if not matches:
            raise ValueError(f"unknown month in date {s!r}")
        mo, d, y = matches[0], int(m.group(2)), int(m.group(3))
    else:
        raise ValueError(f"unrecognised date {s!r}")
    try:
        return date(y, mo, d)
    except ValueError:
        raise ValueError(f"invalid date {s!r}") from None


_AMOUNT = re.compile(r"(-)?([$£€])?(\d[\d,]*(?:\.\d+)?)")


def parse_amount(text: str) -> Decimal:
    s = text.strip()
    negative = False
    if s.startswith("(") and s.endswith(")"):
        negative, s = True, s[1:-1].strip()
    m = _AMOUNT.fullmatch(s)
    if not m:
        raise ValueError(f"unrecognised amount {text.strip()!r}")
    if m.group(1):
        if negative:
            raise ValueError(f"unrecognised amount {text.strip()!r}")
        negative = True
    number = m.group(3).replace(",", "")
    if "." in number and len(number.split(".")[1]) > 2:
        raise ValueError(f"more than two decimals in {text.strip()!r}")
    value = money(Decimal(number))
    return -value if negative else value


def parse_csv(text: str, strict: bool = True) -> ParseResult:
    reader = csv.reader(io.StringIO(text))
    result = ParseResult()
    header = None
    for row in reader:
        line = reader.line_num
        if not any(cell.strip() for cell in row):
            continue
        if header is None:
            names = [cell.strip().lower() for cell in row]
            for need in ("date", "payee", "amount"):
                if need not in names:
                    raise ParseError(line, f"missing column {need!r}")
            header = {name: names.index(name) for name in ("date", "payee", "amount", "category") if name in names}
            continue

        def cell(name):
            i = header.get(name)
            return row[i].strip() if i is not None and i < len(row) else ""

        try:
            payee = cell("payee")
            if not payee:
                raise ValueError("empty payee")
            txn = Transaction(parse_date(cell("date")), payee, parse_amount(cell("amount")),
                              cell("category").lower() or "uncategorized")
        except ValueError as e:
            error = ParseError(line, str(e))
            if strict:
                raise error from None
            result.errors.append(error)
            continue
        result.transactions.append(txn)
    return result
