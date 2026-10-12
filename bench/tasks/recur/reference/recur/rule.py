import re
from dataclasses import dataclass
from datetime import date

FREQS = ("DAILY", "WEEKLY", "MONTHLY", "YEARLY")
DAYS = ("MO", "TU", "WE", "TH", "FR", "SA", "SU")


@dataclass(frozen=True)
class Rule:
    freq: str
    interval: int = 1
    count: int | None = None
    until: date | None = None
    bymonth: tuple = ()
    bymonthday: tuple = ()
    byyearday: tuple = ()
    byday: tuple = ()
    bysetpos: tuple = ()
    wkst: int = 0


def _int(key, text, low, high, zero=False):
    if not re.fullmatch(r"[+-]?\d+", text):
        raise ValueError(f"{key}: not a number: {text!r}")
    n = int(text)
    if not (low <= abs(n) <= high) or (n < 0 and low > 0 and key in ("INTERVAL", "COUNT", "BYMONTH")) or (n == 0 and not zero):
        raise ValueError(f"{key}: out of range: {text!r}")
    return n


def _ints(key, text, high, negative=True):
    out = []
    for part in text.split(","):
        n = _int(key, part, 1, high)
        if n < 0 and not negative:
            raise ValueError(f"{key}: out of range: {part!r}")
        out.append(n)
    return tuple(out)


def _day(text):
    m = re.fullmatch(r"([+-]?\d{1,2})?([A-Z]{2})", text)
    if not m or m.group(2) not in DAYS:
        raise ValueError(f"BYDAY: bad day: {text!r}")
    n = 0
    if m.group(1):
        n = int(m.group(1))
        if not 1 <= abs(n) <= 53:
            raise ValueError(f"BYDAY: ordinal out of range: {text!r}")
    return (n, DAYS.index(m.group(2)))


def _until(text):
    m = re.fullmatch(r"(\d{4})(\d{2})(\d{2})(T\d{6}Z?)?", text)
    if not m:
        raise ValueError(f"UNTIL: bad date: {text!r}")
    try:
        return date(int(m.group(1)), int(m.group(2)), int(m.group(3)))
    except ValueError:
        raise ValueError(f"UNTIL: bad date: {text!r}") from None


def parse_rrule(text: str) -> Rule:
    s = text.strip()
    if s.upper().startswith("RRULE:"):
        s = s[6:]
    if not s:
        raise ValueError("empty rule")
    fields = {}
    for part in s.split(";"):
        if "=" not in part:
            raise ValueError(f"bad part: {part!r}")
        key, value = part.split("=", 1)
        key, value = key.strip().upper(), value.strip().upper()
        if key in fields:
            raise ValueError(f"{key}: given twice")
        fields[key] = value
    if "FREQ" not in fields:
        raise ValueError("FREQ is required")
    freq = fields.pop("FREQ")
    if freq not in FREQS:
        raise ValueError(f"FREQ: unsupported: {freq!r}")
    kw = {"freq": freq}
    for key, value in fields.items():
        if key == "INTERVAL":
            kw["interval"] = _int(key, value, 1, 10**6)
        elif key == "COUNT":
            kw["count"] = _int(key, value, 1, 10**6)
        elif key == "UNTIL":
            kw["until"] = _until(value)
        elif key == "BYMONTH":
            kw["bymonth"] = _ints(key, value, 12, negative=False)
        elif key == "BYMONTHDAY":
            kw["bymonthday"] = _ints(key, value, 31)
        elif key == "BYYEARDAY":
            kw["byyearday"] = _ints(key, value, 366)
        elif key == "BYSETPOS":
            kw["bysetpos"] = _ints(key, value, 366)
        elif key == "BYDAY":
            kw["byday"] = tuple(_day(p) for p in value.split(","))
        elif key == "WKST":
            if value not in DAYS:
                raise ValueError(f"WKST: bad day: {value!r}")
            kw["wkst"] = DAYS.index(value)
        else:
            raise ValueError(f"unknown key: {key}")
    if "count" in kw and "until" in kw:
        raise ValueError("COUNT and UNTIL cannot both be given")
    if any(n for n, _ in kw.get("byday", ())) and freq in ("DAILY", "WEEKLY"):
        raise ValueError("BYDAY ordinals need MONTHLY or YEARLY")
    if kw.get("bymonthday") and freq == "WEEKLY":
        raise ValueError("BYMONTHDAY cannot be used with WEEKLY")
    if kw.get("byyearday") and freq != "YEARLY":
        raise ValueError("BYYEARDAY needs YEARLY")
    if kw.get("bysetpos") and not any(kw.get(k) for k in ("bymonth", "bymonthday", "byyearday", "byday")):
        raise ValueError("BYSETPOS needs another BY rule")
    return Rule(**kw)
