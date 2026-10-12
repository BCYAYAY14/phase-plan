from dataclasses import dataclass
from decimal import Decimal

from .model import money

_BANDS = (("weekly", 6, 8), ("monthly", 27, 32), ("yearly", 362, 368))


@dataclass(frozen=True)
class Recurring:
    payee: str
    amount: Decimal
    interval: str
    count: int


def normalize_payee(payee: str) -> str:
    tokens = payee.lower().split()
    while len(tokens) > 1 and any(c.isdigit() for c in tokens[-1]):
        tokens.pop()
    return " ".join(tokens)


def _median(values):
    s = sorted(values)
    mid = len(s) // 2
    return s[mid] if len(s) % 2 else (s[mid - 1] + s[mid]) / 2


def find_recurring(txns) -> list:
    groups = {}
    for t in txns:
        groups.setdefault(normalize_payee(t.payee), []).append(t)
    found = []
    for payee in sorted(groups):
        group = sorted(groups[payee], key=lambda t: t.date)
        if len(group) < 3:
            continue
        median = _median([t.amount for t in group])
        if median == 0 or any(abs(t.amount - median) > abs(median) * Decimal("0.05") for t in group):
            continue
        gaps = [(b.date - a.date).days for a, b in zip(group, group[1:])]
        for name, low, high in _BANDS:
            if all(low <= g <= high for g in gaps):
                found.append(Recurring(payee, money(median), name, len(group)))
                break
    return found
