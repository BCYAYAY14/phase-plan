import tomllib
from dataclasses import dataclass, replace
from decimal import Decimal, InvalidOperation

from .model import money


@dataclass(frozen=True)
class Rule:
    category: str
    payee: str | None = None
    min_amount: Decimal | None = None
    max_amount: Decimal | None = None

    def matches(self, txn) -> bool:
        if self.payee is not None and self.payee.lower() not in txn.payee.lower():
            return False
        if self.min_amount is not None and txn.amount < self.min_amount:
            return False
        if self.max_amount is not None and txn.amount > self.max_amount:
            return False
        return True


_KEYS = {"category", "payee", "min_amount", "max_amount"}


def _amount(n, key, value):
    if isinstance(value, bool) or not isinstance(value, (int, float, str)):
        raise ValueError(f"rule {n}: {key} must be a number")
    try:
        return money(Decimal(str(value)))
    except InvalidOperation:
        raise ValueError(f"rule {n}: {key} must be a number") from None


def load_rules(text: str) -> list:
    data = tomllib.loads(text)
    rules = []
    for n, raw in enumerate(data.get("rule", []), 1):
        unknown = sorted(set(raw) - _KEYS)
        if unknown:
            raise ValueError(f"rule {n}: unknown key {unknown[0]!r}")
        category = str(raw.get("category", "")).strip().lower()
        if not category:
            raise ValueError(f"rule {n}: missing category")
        low = _amount(n, "min_amount", raw["min_amount"]) if "min_amount" in raw else None
        high = _amount(n, "max_amount", raw["max_amount"]) if "max_amount" in raw else None
        payee = str(raw["payee"]) if "payee" in raw else None
        if payee is None and low is None and high is None:
            raise ValueError(f"rule {n}: no condition")
        rules.append(Rule(category, payee, low, high))
    return rules


def apply_rules(txns, rules, overwrite: bool = False) -> list:
    out = []
    for t in txns:
        if overwrite or t.category == "uncategorized":
            for rule in rules:
                if rule.matches(t):
                    t = replace(t, category=rule.category)
                    break
        out.append(t)
    return out
