from dataclasses import dataclass
from datetime import date


@dataclass(frozen=True)
class Rule:
    freq: str
    interval: int = 1
    count: int | None = None
    until: date | None = None


def parse_rrule(text):
    fields = dict(part.split("=", 1) for part in text.split(";"))
    until = fields.get("UNTIL")
    return Rule(
        freq=fields["FREQ"],
        interval=int(fields.get("INTERVAL", 1)),
        count=int(fields["COUNT"]) if "COUNT" in fields else None,
        until=date(int(until[:4]), int(until[4:6]), int(until[6:8])) if until else None,
    )
