import re
from datetime import date

from .model import Transaction
from .parse import ParseError, ParseResult, parse_amount


def _date(text: str) -> date:
    s = text.strip()
    m = re.fullmatch(r"(\d{1,2})/(\d{1,2})(?:/(\d{4})|'(\d{2}))", s)
    if not m:
        raise ValueError(f"unrecognised date {s!r}")
    month, day = int(m.group(1)), int(m.group(2))
    year = int(m.group(3)) if m.group(3) else 2000 + int(m.group(4))
    try:
        return date(year, month, day)
    except ValueError:
        raise ValueError(f"invalid date {s!r}") from None


def _record(start, fields) -> Transaction:
    for code, name in (("D", "date"), ("T", "amount"), ("P", "payee")):
        if code not in fields:
            raise ParseError(start, f"missing {name}")

    def field(code, convert):
        line, value = fields[code]
        try:
            return convert(value)
        except ValueError as e:
            raise ParseError(line, str(e)) from None

    when = field("D", _date)
    amount = field("T", parse_amount)
    line, payee = fields["P"]
    payee = payee.strip()
    if not payee:
        raise ParseError(line, "empty payee")
    category = fields.get("L", (0, ""))[1].strip()
    category = "transfer" if category.startswith("[") else (category.lower() or "uncategorized")
    return Transaction(when, payee, amount, category)


def parse_qif(text: str, strict: bool = True) -> ParseResult:
    result = ParseResult()
    start, fields = None, {}

    def finish():
        if start is None:
            return
        try:
            result.transactions.append(_record(start, fields))
        except ParseError as e:
            if strict:
                raise
            result.errors.append(e)

    for n, raw in enumerate(text.splitlines(), 1):
        s = raw.strip()
        if not s or s.startswith("!"):
            continue
        if s == "^":
            finish()
            start, fields = None, {}
            continue
        if start is None:
            start = n
        if s[0] in "DTPL":
            fields.setdefault(s[0], (n, s[1:]))
    finish()
    return result
