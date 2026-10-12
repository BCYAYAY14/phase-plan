# ledger: specification

A command-line tool that reads a bank's CSV export and reports on it. Python 3.10 or later, standard library only. The public names below are a contract: other code imports them, so keep the module paths, names, fields and signatures exactly.

## Money

Every amount is a `decimal.Decimal` quantized to two places with `ROUND_HALF_UP`. No `float` anywhere in a computation or a result. JSON output writes amounts as strings with exactly two decimals (`"12.30"`, `"-4.00"`).

## `ledger.model`

- `Transaction`: a frozen dataclass with fields, in order, `date: datetime.date`, `payee: str`, `amount: Decimal`, `category: str = "uncategorized"`.
- `money(value) -> Decimal`: quantizes to two places, `ROUND_HALF_UP`.

## `ledger.parse`

- `ParseError(Exception)`: has `.line` (an int) and `.message` (a str); `str(error)` is `"line <line>: <message>"`.
- `ParseResult`: has `.transactions` (a list of `Transaction`) and `.errors` (a list of `ParseError`).
- `parse_csv(text: str, strict: bool = True) -> ParseResult`.

Rules:
1. The first non-blank row is the header. Column names are matched case-insensitively and with surrounding spaces removed. `date`, `payee` and `amount` are required; `category` is optional; any other column is ignored; column order is free. A missing required column raises `ParseError` on the header's line, whatever `strict` is.
2. Blank rows (every cell empty or spaces) are skipped anywhere.
3. Line numbers are the physical line in the text, counting the header's line; quoted fields follow the `csv` module.
4. `date` accepts exactly three forms: `YYYY-MM-DD`; `DD/MM/YYYY` (day first; day and month may be one or two digits); and an English month name, full or three-letter, any case, then the day and a comma: `Mar 5, 2026`, `march 05, 2026`. A date that does not exist (`2026-02-30`) is an error.
5. `amount` accepts an optional leading `-` or surrounding parentheses (either means negative, not both), then an optional currency symbol `$`, `£` or `€`, then digits with optional `,` thousands separators and at most two decimals. Examples: `12`, `1,234.56`, `-$5.00`, `($1,000.10)`, `€3.5`. More than two decimals, an empty amount, or anything else is an error.
6. `payee` is kept as written, with surrounding spaces removed; an empty payee is an error.
7. `category` is lower-cased and stripped; empty or missing becomes `"uncategorized"`.
8. With `strict=True`, the first bad row raises its `ParseError`. With `strict=False`, bad rows are skipped and collected in `.errors`, in order.

## `ledger.reports`

- `balance(txns, as_of: date | None = None) -> Decimal`: the sum of amounts dated on or before `as_of` (all of them when `None`).
- `by_category(txns) -> dict[str, Decimal]`: the total per category, keys in ascending order.
- `MonthRow`: a frozen dataclass `month: str` (`"YYYY-MM"`), `income: Decimal`, `expense: Decimal`, `net: Decimal`.
- `monthly(txns) -> list[MonthRow]`: one row per calendar month from the earliest transaction's month to the latest's, months with no transactions included (all zero). `income` is the sum of positive amounts, `expense` the sum of negative amounts as a positive number, `net = income - expense`. No transactions gives `[]`.

## `ledger.recurring`

- `Recurring`: a frozen dataclass `payee: str`, `amount: Decimal`, `interval: str`, `count: int`.
- `normalize_payee(payee: str) -> str`: lower-case, split on whitespace, drop trailing tokens that contain a digit while more than one token remains, join with single spaces. `"NETFLIX.COM 8842"` gives `"netflix.com"`; `"Spotify  #1234"` gives `"spotify"`; `"7-Eleven"` gives `"7-eleven"`.
- `find_recurring(txns) -> list[Recurring]`: group by normalized payee. A group is recurring when it has at least 3 transactions, its median amount is not zero, every amount is within 5% of the median (`abs(a - median) <= abs(median) * 0.05`), and every gap in days between consecutive transactions (sorted by date) falls in one band: weekly 6 to 8, monthly 27 to 32, yearly 362 to 368 (inclusive). `payee` is the normalized name, `amount` the median (the mean of the middle two for an even count) through `money`, `count` the group's size. Sorted by payee.

## Command line

`python3 -m ledger FILE COMMAND [--json] [--as-of YYYY-MM-DD] [--lenient]`, where `COMMAND` is `balance`, `categories`, `monthly` or `recurring`.

- `--as-of` keeps only transactions on or before the date, for every command.
- `--lenient` parses with `strict=False` and prints `skipped line N: message` to stderr for each skipped row.
- `balance` prints `Balance: 123.45`; with `--json`, `{"balance": "123.45"}`.
- `categories --json`: an object of category to amount, keys ascending.
- `monthly --json`: a list of `{"month", "income", "expense", "net"}` objects.
- `recurring --json`: a list of `{"payee", "amount", "interval", "count"}` objects (`count` an integer).
- Text output for `categories`, `monthly` and `recurring` is free, but must be readable and aligned.

Exit codes: 0 on success; 1 when the file cannot be read or `--as-of` is not a valid date, with `error: ...` on stderr; 2 on a parse error without `--lenient`, printing `line N: message` to stderr. Nothing goes to stdout on a failure.
