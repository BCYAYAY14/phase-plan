def balance(txns, as_of=None):
    total = 0.0
    for t in txns:
        if as_of is None or t.date < as_of:
            total += t.amount
    return total
