# recur: specification

Expands recurrence rules (a subset of iCalendar's RRULE, RFC 5545) into dates. Python 3.11 or later, standard library only. Dates only: no times, no time zones. The public names below are a contract: keep module paths, names, fields and signatures exactly.

## `recur.rule`

- `Rule`: a frozen dataclass with fields in this order: `freq: str` (`"DAILY"`, `"WEEKLY"`, `"MONTHLY"` or `"YEARLY"`), `interval: int = 1`, `count: int | None = None`, `until: date | None = None`, `bymonth: tuple = ()`, `bymonthday: tuple = ()`, `byyearday: tuple = ()`, `byday: tuple = ()`, `bysetpos: tuple = ()`, `wkst: int = 0`. Weekdays are numbered as `date.weekday()`: Monday 0 to Sunday 6. `byday` holds `(ordinal, weekday)` pairs, ordinal 0 meaning "every"; the other tuples hold ints in the order written.
- `parse_rrule(text: str) -> Rule`. Raises `ValueError` for anything outside these rules.

Syntax: an optional `RRULE:` prefix, then `KEY=VALUE` parts separated by `;`, in any order; keys and values are case-insensitive; a key may appear once.
- `FREQ` is required: `DAILY`, `WEEKLY`, `MONTHLY` or `YEARLY`.
- `INTERVAL`, `COUNT`: positive integers. `COUNT` and `UNTIL` cannot both be given.
- `UNTIL`: `YYYYMMDD`, optionally followed by a time `THHMMSS` or `THHMMSSZ`, which is ignored. The date must exist.
- `BYMONTH`: comma-separated 1 to 12. `BYMONTHDAY`: 1 to 31 or -31 to -1 (from the month's end, -1 the last day). `BYYEARDAY`: 1 to 366 or -366 to -1. `BYSETPOS`: 1 to 366 or -366 to -1.
- `BYDAY`: comma-separated two-letter days `MO TU WE TH FR SA SU`, each optionally prefixed with an ordinal 1 to 53 or -53 to -1 (`1FR`, `-1SU`, `+2MO`).
- `WKST`: a two-letter day; default `MO`.
- Combinations refused: an ordinal in `BYDAY` with `DAILY` or `WEEKLY`; `BYMONTHDAY` with `WEEKLY`; `BYYEARDAY` with anything but `YEARLY`; `BYSETPOS` with no other `BY` rule.

## `recur.expand`

- `occurrences(rule: Rule, dtstart: date, end: date | None = None, limit: int | None = None) -> list[date]`: the occurrences in order. It stops at `COUNT` occurrences, after `UNTIL` (inclusive), after `end` (inclusive), or at `limit` occurrences, whichever comes first. With no `COUNT`, `UNTIL`, `end` or `limit` it raises `ValueError`. It never looks more than 400 years past `dtstart`'s year, so a rule that can never match returns `[]`.

How the dates are found:
1. **Periods.** `DAILY`: one day. `WEEKLY`: a week starting on `WKST`. `MONTHLY`: a calendar month. `YEARLY`: a calendar year. Periods are counted from the one containing `dtstart`, and only every `INTERVAL`-th one is used (the first, then `INTERVAL` later, and so on).
2. **Defaults.** Taken from `dtstart` when the rule says nothing finer. `WEEKLY` without `BYDAY`: `dtstart`'s weekday. `MONTHLY` without `BYMONTHDAY` or `BYDAY`: `dtstart`'s day of month. `YEARLY` without `BYYEARDAY`, `BYMONTHDAY` or `BYDAY`: `dtstart`'s day of month, and `dtstart`'s month unless `BYMONTH` is given.
3. **Candidates.** The days of a used period that pass every `BY` rule present (after defaults): the month is in `BYMONTH`; the day of the year, counted from the start or (negative) from the end, is in `BYYEARDAY`; the day of the month, likewise, is in `BYMONTHDAY`; and the weekday is in `BYDAY`. A `BYDAY` ordinal `n` keeps only the n-th such weekday (negative: from the end) of the month when `FREQ` is `MONTHLY`, or `YEARLY` with `BYMONTH`; otherwise of the year. A day that does not exist (February 30) is never a candidate.
4. **BYSETPOS.** If given, only the candidates at those positions in the period's sorted candidates are kept (1 the first, -1 the last); positions outside the list are ignored.
5. **Bounds.** Candidates before `dtstart` are dropped. `dtstart` itself is an occurrence only when the rule produces it. Then `COUNT`, `UNTIL`, `end` and `limit` apply, in date order.

## `recur.ics`

- `event_dates(text: str, end: date) -> list[date]`: the dates of the one event in an iCalendar text, sorted, without duplicates, none after `end`.
- Lines end with `\n` or `\r\n`. A line starting with a space or tab continues the previous line (remove the line break and that one character). A property is `NAME[;PARAMS]:VALUE`; names are case-insensitive; lines without a known name are ignored.
- `DTSTART` (required) is a date `YYYYMMDD` (a time part, if any, is ignored); it is always one of the event's dates, even when the rule does not produce it. `RRULE` (at most one) is parsed with `parse_rrule` and expanded from `DTSTART` up to `end`. `RDATE` adds dates and `EXDATE` removes dates; each may appear on several lines with comma-separated values. A bad or missing date, or a bad rule, raises `ValueError`.

## Command line

`python3 -m recur RULE --start YYYY-MM-DD [--end YYYY-MM-DD] [--limit N] [--json]` lists a rule's occurrences; `python3 -m recur --ics FILE --end YYYY-MM-DD [--limit N] [--json]` lists an event's dates (`--limit` keeps the first N).
- Output: one ISO date per line, or with `--json` a JSON list of ISO date strings.
- Exit code 1 with `error: ...` on stderr, and nothing on stdout, for: a bad rule, a rule with no bound (no `COUNT`, `UNTIL`, `--end` or `--limit`), a bad date, a missing `--start` with a rule, a missing `--end` with `--ics`, both a rule and `--ics`, a file that cannot be read, or a bad event.
