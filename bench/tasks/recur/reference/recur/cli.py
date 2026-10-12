import argparse
import json
import sys
from datetime import date

from .expand import occurrences
from .ics import event_dates
from .rule import parse_rrule


def _date(flag, value):
    try:
        return date.fromisoformat(value)
    except ValueError:
        raise ValueError(f"{flag} must be YYYY-MM-DD") from None


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(prog="recur", description="Expand recurrence rules.")
    ap.add_argument("rule", nargs="?", help="an RRULE, e.g. FREQ=MONTHLY;BYDAY=-1FR")
    ap.add_argument("--start", help="first date, YYYY-MM-DD (with a rule)")
    ap.add_argument("--ics", help="an .ics file holding one event")
    ap.add_argument("--end", help="last date to list, YYYY-MM-DD")
    ap.add_argument("--limit", type=int, help="list at most N dates")
    ap.add_argument("--json", action="store_true")
    args = ap.parse_args(argv)
    try:
        end = _date("--end", args.end) if args.end else None
        if args.ics:
            if args.rule:
                raise ValueError("give a rule or --ics, not both")
            if end is None:
                raise ValueError("--ics needs --end")
            try:
                with open(args.ics, encoding="utf-8") as f:
                    text = f.read()
            except OSError as e:
                raise ValueError(str(e)) from None
            found = event_dates(text, end)
            if args.limit is not None:
                found = found[: args.limit]
        else:
            if not args.rule or not args.start:
                raise ValueError("give a rule and --start, or --ics")
            if args.limit is not None and args.limit < 1:
                raise ValueError("--limit must be at least 1")
            found = occurrences(parse_rrule(args.rule), _date("--start", args.start), end=end, limit=args.limit)
    except ValueError as e:
        print(f"error: {e}", file=sys.stderr)
        return 1
    if args.json:
        print(json.dumps([d.isoformat() for d in found]))
    else:
        for d in found:
            print(d.isoformat())
    return 0
