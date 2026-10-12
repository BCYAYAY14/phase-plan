import re
import tomllib
from dataclasses import dataclass
from decimal import Decimal, InvalidOperation

from .model import money


@dataclass(frozen=True)
class BudgetLine:
    category: str
    budget: Decimal
    spent: Decimal
    remaining: Decimal
    status: str


def load_budgets(text: str) -> dict:
    table = tomllib.loads(text).get("budgets", {})
    out = {}
    for name, value in table.items():
        amount = None
        if not isinstance(value, bool) and isinstance(value, (int, float, str)):
            try:
                amount = money(Decimal(str(value)))
            except InvalidOperation:
                pass
        if amount is None or amount <= 0:
            raise ValueError(f"budget {name!r}: must be a positive amount")
        out[name.strip().lower()] = amount
    return out


def budget_report(txns, budgets, month: str) -> list:
    if not re.fullmatch(r"\d{4}-(0[1-9]|1[0-2])", month):
        raise ValueError(f"invalid month {month!r}")
    y, m = map(int, month.split("-"))
    lines = []
    for category in sorted(budgets):
        budget = budgets[category]
        total = sum((t.amount for t in txns if t.category == category and (t.date.year, t.date.month) == (y, m)), Decimal(0))
        spent = money(Decimal(0) - total)
        status = "over" if spent > budget else "warn" if spent >= budget * Decimal("0.8") else "ok"
        lines.append(BudgetLine(category, budget, spent, money(budget - spent), status))
    return lines
