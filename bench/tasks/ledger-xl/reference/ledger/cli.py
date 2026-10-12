import argparse
import json
import sys
from datetime import date

from .budget import budget_report, load_budgets
from .dedupe import find_duplicates, merge
from .export import to_csv
from .forecast import project
from .parse import ParseError, parse_csv
from .qif import parse_qif
from .recurring import find_recurring
from .reports import balance, by_category, monthly
from .rules import apply_rules, load_rules

COMMANDS = ["balance", "categories", "monthly", "recurring", "dupes", "budget", "forecast", "export"]


class Fail(Exception):
    def __init__(self, code, message):
        super().__init__(message)
        self.code = code


def _read(path):
    try:
        with open(path, encoding="utf-8") as f:
            return f.read()
    except OSError as e:
        raise Fail(1, f"error: {e}") from None


def _date(flag, value):
    try:
        return date.fromisoformat(value)
    except ValueError:
        raise Fail(1, f"error: {flag} must be YYYY-MM-DD") from None


def _load(path, lenient, prefix):
    text = _read(path)
    parse = parse_qif if path.lower().endswith(".qif") else parse_csv
    try:
        result = parse(text, strict=not lenient)
    except ParseError as e:
        raise Fail(2, f"{prefix}{e}") from None
    for e in result.errors:
        print(f"skipped {prefix}{e}", file=sys.stderr)
    return result.transactions


def _txn(t):
    return {"date": t.date.isoformat(), "payee": t.payee, "amount": str(t.amount), "category": t.category}


def run(args):
    as_of = _date("--as-of", args.as_of) if args.as_of else None
    until = _date("--until", args.until) if args.until else None
    if args.command == "budget" and not (args.budgets and args.month):
        raise Fail(1, "error: budget needs --budgets and --month")
    if args.command == "forecast" and until is None:
        raise Fail(1, "error: forecast needs --until")
    rules = budgets = None
    try:
        if args.rules:
            rules = load_rules(_read(args.rules))
        if args.budgets:
            budgets = load_budgets(_read(args.budgets))
    except ValueError as e:
        raise Fail(1, f"error: {e}") from None

    txns = _load(args.file, args.lenient, "")
    if args.also:
        txns = merge(txns, *(_load(p, args.lenient, f"{p}: ") for p in args.also))
    if as_of is not None:
        txns = [t for t in txns if t.date <= as_of]
    if rules:
        txns = apply_rules(txns, rules)

    out = []
    if args.command == "balance":
        value = balance(txns)
        out.append(json.dumps({"balance": str(value)}) if args.json else f"Balance: {value}")
    elif args.command == "categories":
        totals = by_category(txns)
        if args.json:
            out.append(json.dumps({k: str(v) for k, v in totals.items()}))
        else:
            width = max((len(k) for k in totals), default=0)
            out += [f"{k.ljust(width)}  {v:>12}" for k, v in totals.items()]
    elif args.command == "monthly":
        rows = monthly(txns)
        if args.json:
            out.append(json.dumps([{"month": r.month, "income": str(r.income), "expense": str(r.expense),
                                    "net": str(r.net)} for r in rows]))
        else:
            out.append(f"{'month':7}  {'income':>12}  {'expense':>12}  {'net':>12}")
            out += [f"{r.month:7}  {r.income:>12}  {r.expense:>12}  {r.net:>12}" for r in rows]
    elif args.command == "recurring":
        found = find_recurring(txns)
        if args.json:
            out.append(json.dumps([{"payee": r.payee, "amount": str(r.amount), "interval": r.interval,
                                    "count": r.count} for r in found]))
        else:
            out += [f"{r.payee}: {r.amount} {r.interval} ({r.count} times)" for r in found]
    elif args.command == "dupes":
        groups = find_duplicates(txns)
        if args.json:
            out.append(json.dumps([[_txn(t) for t in g] for g in groups]))
        else:
            for g in groups:
                out.append(f"{g[0].date} {g[0].payee} {g[0].amount} x{len(g)}")
    elif args.command == "budget":
        try:
            lines = budget_report(txns, budgets, args.month)
        except ValueError as e:
            raise Fail(1, f"error: {e}") from None
        if args.json:
            out.append(json.dumps([{"category": b.category, "budget": str(b.budget), "spent": str(b.spent),
                                    "remaining": str(b.remaining), "status": b.status} for b in lines]))
        else:
            width = max((len(b.category) for b in lines), default=0)
            out += [f"{b.category.ljust(width)}  {b.spent:>10} of {b.budget:>10}  {b.status}" for b in lines]
    elif args.command == "forecast":
        future = project(txns, until)
        if args.json:
            out.append(json.dumps([_txn(t) for t in future]))
        else:
            out += [f"{t.date}  {t.payee}  {t.amount}" for t in future]
    else:
        sys.stdout.write(to_csv(txns))
        return
    print("\n".join(out))


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(prog="ledger", description="Reports on a bank CSV or QIF file.")
    ap.add_argument("file")
    ap.add_argument("command", choices=COMMANDS)
    ap.add_argument("--json", action="store_true", help="print JSON")
    ap.add_argument("--as-of", help="only transactions on or before YYYY-MM-DD")
    ap.add_argument("--lenient", action="store_true", help="skip bad rows instead of stopping")
    ap.add_argument("--rules", help="TOML file of categorisation rules")
    ap.add_argument("--also", action="append", default=[], help="another statement to merge in (repeatable)")
    ap.add_argument("--budgets", help="TOML file of monthly budgets")
    ap.add_argument("--month", help="YYYY-MM, for budget")
    ap.add_argument("--until", help="YYYY-MM-DD, for forecast")
    args = ap.parse_args(argv)
    try:
        run(args)
    except Fail as e:
        print(str(e), file=sys.stderr)
        return e.code
    return 0
