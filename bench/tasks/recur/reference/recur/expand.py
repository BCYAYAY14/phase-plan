import calendar
from datetime import date, timedelta

from .rule import Rule

_HORIZON_YEARS = 400


def _period(rule, dtstart, k):
    """The k-th used period (k counts used periods) as (first day, last day)."""
    step = k * rule.interval
    if rule.freq == "DAILY":
        d = dtstart + timedelta(days=step)
        return d, d
    if rule.freq == "WEEKLY":
        start = dtstart - timedelta(days=(dtstart.weekday() - rule.wkst) % 7) + timedelta(weeks=step)
        return start, start + timedelta(days=6)
    if rule.freq == "MONTHLY":
        index = dtstart.month - 1 + step
        y, m = dtstart.year + index // 12, index % 12 + 1
        return date(y, m, 1), date(y, m, calendar.monthrange(y, m)[1])
    y = dtstart.year + step
    return date(y, 1, 1), date(y, 12, 31)


def _nth_ok(d, n, scope_first, scope_last):
    if n > 0:
        return (d - scope_first).days // 7 + 1 == n
    return (scope_last - d).days // 7 + 1 == -n


def _candidates(rule, dtstart, first, last):
    bymonth, bymonthday, byday = rule.bymonth, rule.bymonthday, rule.byday
    if rule.freq == "WEEKLY" and not byday:
        byday = ((0, dtstart.weekday()),)
    if rule.freq == "MONTHLY" and not (bymonthday or byday):
        bymonthday = (dtstart.day,)
    if rule.freq == "YEARLY" and not (rule.byyearday or bymonthday or byday):
        bymonthday = (dtstart.day,)
        bymonth = bymonth or (dtstart.month,)
    month_scope = rule.freq == "MONTHLY" or (rule.freq == "YEARLY" and bool(rule.bymonth))
    out = []
    d = first
    while d <= last:
        mlen = calendar.monthrange(d.year, d.month)[1]
        ylen = 366 if calendar.isleap(d.year) else 365
        yday = d.timetuple().tm_yday
        ok = True
        if bymonth and d.month not in bymonth:
            ok = False
        elif rule.byyearday and yday not in rule.byyearday and yday - ylen - 1 not in rule.byyearday:
            ok = False
        elif bymonthday and d.day not in bymonthday and d.day - mlen - 1 not in bymonthday:
            ok = False
        elif byday:
            if month_scope:
                s_first, s_last = date(d.year, d.month, 1), date(d.year, d.month, mlen)
            else:
                s_first, s_last = date(d.year, 1, 1), date(d.year, 12, 31)
            ok = any(wd == d.weekday() and (n == 0 or _nth_ok(d, n, s_first, s_last)) for n, wd in byday)
        if ok:
            out.append(d)
        d += timedelta(days=1)
    if rule.bysetpos:
        picked = set()
        for p in rule.bysetpos:
            i = p - 1 if p > 0 else len(out) + p
            if 0 <= i < len(out):
                picked.add(out[i])
        out = sorted(picked)
    return out


def occurrences(rule: Rule, dtstart: date, end: date | None = None, limit: int | None = None) -> list:
    if rule.count is None and rule.until is None and end is None and limit is None:
        raise ValueError("unbounded rule: give COUNT, UNTIL, an end or a limit")
    stop = min(x for x in (rule.until, end, date(min(dtstart.year + _HORIZON_YEARS, 9999), 12, 31)) if x is not None)
    out = []
    k = 0
    while True:
        first, last = _period(rule, dtstart, k)
        if first > stop:
            return out
        for d in _candidates(rule, dtstart, first, last):
            if d < dtstart:
                continue
            if d > stop:
                return out
            out.append(d)
            if (rule.count is not None and len(out) >= rule.count) or (limit is not None and len(out) >= limit):
                return out
        k += 1
