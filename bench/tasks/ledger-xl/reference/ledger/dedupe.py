from collections import Counter

from .recurring import normalize_payee


def _key(t):
    return (t.date, normalize_payee(t.payee), t.amount)


def find_duplicates(txns) -> list:
    groups = {}
    for t in txns:
        groups.setdefault(_key(t), []).append(t)
    return [g for k, g in sorted(groups.items(), key=lambda kg: kg[0]) if len(g) > 1]


def merge(*statements) -> list:
    need = Counter()
    for statement in statements:
        for key, count in Counter(map(_key, statement)).items():
            need[key] = max(need[key], count)
    taken = Counter()
    out = []
    for statement in statements:
        for t in statement:
            key = _key(t)
            if taken[key] < need[key]:
                taken[key] += 1
                out.append(t)
    return sorted(out, key=lambda t: t.date)
