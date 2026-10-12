import calendar
from datetime import date, timedelta

from .model import Transaction
from .recurring import find_recurring, normalize_payee


def _clamped(year, month, day):
    return date(year, month, min(day, calendar.monthrange(year, month)[1]))


def project(txns, until: date) -> list:
    out = []
    for r in find_recurring(txns):
        group = sorted((t for t in txns if normalize_payee(t.payee) == r.payee), key=lambda t: t.date)
        first, last = group[0], group[-1]
        k = 1
        while True:
            if r.interval == "weekly":
                when = last.date + timedelta(days=7 * k)
            elif r.interval == "monthly":
                index = last.date.month - 1 + k
                when = _clamped(last.date.year + index // 12, index % 12 + 1, first.date.day)
            else:
                when = _clamped(last.date.year + k, first.date.month, first.date.day)
            if when > until:
                break
            out.append(Transaction(when, last.payee, r.amount, last.category))
            k += 1
    return sorted(out, key=lambda t: (t.date, normalize_payee(t.payee)))
