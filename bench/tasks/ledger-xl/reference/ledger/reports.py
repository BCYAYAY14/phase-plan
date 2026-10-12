from dataclasses import dataclass
from decimal import Decimal

from .model import money


@dataclass(frozen=True)
class MonthRow:
    month: str
    income: Decimal
    expense: Decimal
    net: Decimal


def balance(txns, as_of=None) -> Decimal:
    return money(sum((t.amount for t in txns if as_of is None or t.date <= as_of), Decimal(0)))


def by_category(txns) -> dict:
    totals = {}
    for t in txns:
        totals[t.category] = totals.get(t.category, Decimal(0)) + t.amount
    return {name: money(totals[name]) for name in sorted(totals)}


def monthly(txns) -> list:
    if not txns:
        return []
    first = min(t.date for t in txns)
    last = max(t.date for t in txns)
    rows = []
    y, m = first.year, first.month
    while (y, m) <= (last.year, last.month):
        inside = [t.amount for t in txns if (t.date.year, t.date.month) == (y, m)]
        income = sum((a for a in inside if a > 0), Decimal(0))
        expense = Decimal(0) - sum((a for a in inside if a < 0), Decimal(0))
        rows.append(MonthRow(f"{y:04d}-{m:02d}", money(income), money(expense), money(income - expense)))
        y, m = (y + 1, 1) if m == 12 else (y, m + 1)
    return rows
