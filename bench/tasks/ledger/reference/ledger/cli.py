import argparse
import json
import sys
from datetime import date

from .parse import ParseError, parse_csv
from .recurring import find_recurring
from .reports import balance, by_category, monthly


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(prog="ledger", description="Reports on a bank CSV.")
    ap.add_argument("file")
    ap.add_argument("command", choices=["balance", "categories", "monthly", "recurring"])
    ap.add_argument("--json", action="store_true", help="print JSON")
    ap.add_argument("--as-of", help="only transactions on or before YYYY-MM-DD")
    ap.add_argument("--lenient", action="store_true", help="skip bad rows instead of stopping")
    args = ap.parse_args(argv)

    try:
        with open(args.file, encoding="utf-8") as f:
            text = f.read()
    except OSError as e:
        print(f"error: {e}", file=sys.stderr)
        return 1
    as_of = None
    if args.as_of:
        try:
            as_of = date.fromisoformat(args.as_of)
        except ValueError:
            print("error: --as-of must be YYYY-MM-DD", file=sys.stderr)
            return 1
    try:
        result = parse_csv(text, strict=not args.lenient)
    except ParseError as e:
        print(str(e), file=sys.stderr)
        return 2
    for e in result.errors:
        print(f"skipped {e}", file=sys.stderr)
    txns = [t for t in result.transactions if as_of is None or t.date <= as_of]

    if args.command == "balance":
        value = balance(txns)
        print(json.dumps({"balance": str(value)}) if args.json else f"Balance: {value}")
    elif args.command == "categories":
        totals = by_category(txns)
        if args.json:
            print(json.dumps({k: str(v) for k, v in totals.items()}))
        else:
            width = max((len(k) for k in totals), default=0)
            for k, v in totals.items():
                print(f"{k.ljust(width)}  {v:>12}")
    elif args.command == "monthly":
        rows = monthly(txns)
        if args.json:
            print(json.dumps([{"month": r.month, "income": str(r.income), "expense": str(r.expense),
                               "net": str(r.net)} for r in rows]))
        else:
            print(f"{'month':7}  {'income':>12}  {'expense':>12}  {'net':>12}")
            for r in rows:
                print(f"{r.month:7}  {r.income:>12}  {r.expense:>12}  {r.net:>12}")
    else:
        found = find_recurring(txns)
        if args.json:
            print(json.dumps([{"payee": r.payee, "amount": str(r.amount), "interval": r.interval,
                               "count": r.count} for r in found]))
        else:
            for r in found:
                print(f"{r.payee}: {r.amount} {r.interval} ({r.count} times)")
    return 0
