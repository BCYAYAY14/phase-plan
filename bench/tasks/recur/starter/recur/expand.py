from datetime import timedelta


def occurrences(rule, dtstart, end=None, limit=None):
    out = []
    d = dtstart
    while True:
        if rule.until and d > rule.until or end and d > end:
            return out
        out.append(d)
        if rule.count and len(out) >= rule.count or limit and len(out) >= limit:
            return out
        if rule.freq == "DAILY":
            d += timedelta(days=rule.interval)
        elif rule.freq == "WEEKLY":
            d += timedelta(weeks=rule.interval)
        elif rule.freq == "MONTHLY":
            m = d.month - 1 + rule.interval
            d = d.replace(year=d.year + m // 12, month=m % 12 + 1)
        else:
            d = d.replace(year=d.year + rule.interval)
