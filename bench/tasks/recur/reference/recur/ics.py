from datetime import date

from .expand import occurrences
from .rule import parse_rrule


def _dates(value, prop):
    out = []
    for part in value.split(","):
        part = part.strip()
        if len(part) < 8 or not part[:8].isdigit():
            raise ValueError(f"{prop}: bad date: {part!r}")
        try:
            out.append(date(int(part[:4]), int(part[4:6]), int(part[6:8])))
        except ValueError:
            raise ValueError(f"{prop}: bad date: {part!r}") from None
    return out


def event_dates(text: str, end: date) -> list:
    lines = []
    for raw in text.replace("\r\n", "\n").split("\n"):
        if raw[:1] in (" ", "\t") and lines:
            lines[-1] += raw[1:]
        else:
            lines.append(raw)
    dtstart, rrule, rdates, exdates = None, None, [], set()
    for line in lines:
        if ":" not in line:
            continue
        head, value = line.split(":", 1)
        name = head.split(";", 1)[0].strip().upper()
        if name == "DTSTART":
            dtstart = _dates(value, "DTSTART")[0]
        elif name == "RRULE":
            rrule = parse_rrule(value)
        elif name == "RDATE":
            rdates += _dates(value, "RDATE")
        elif name == "EXDATE":
            exdates.update(_dates(value, "EXDATE"))
    if dtstart is None:
        raise ValueError("DTSTART is required")
    found = {dtstart} if dtstart <= end else set()
    if rrule is not None:
        found.update(occurrences(rrule, dtstart, end=end))
    found.update(d for d in rdates if d <= end)
    return sorted(found - exdates)
