# ledger: specification

A command-line tool that reads a bank's CSV export and reports on it. Python 3.11 or later, standard library only (`tomllib` for TOML). The public names below are a contract: other code imports them, so keep the module paths, names, fields and signatures exactly.

## Money

Every amount is a `decimal.Decimal` quantized to two places with `ROUND_HALF_UP`. No `float` anywhere in a computation or a result. JSON output writes amounts as strings with exactly two decimals (`"12.30"`, `"-4.00"`). A zero amount is always `0.00`, never `-0.00`, in any result or output.

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

## `ledger.rules`

- `Rule`: a frozen dataclass `category: str`, `payee: str | None = None`, `min_amount: Decimal | None = None`, `max_amount: Decimal | None = None`.
- `load_rules(text: str) -> list[Rule]`: TOML with an array of tables named `rule`; no `rule` key gives `[]`. Keys: `category` (required), `payee`, `min_amount`, `max_amount` (numbers or numeric strings, through `money`). `category` is lower-cased and stripped. Errors raise `ValueError` with these messages, `N` counting rules from 1: `rule N: missing category` (absent or blank), `rule N: unknown key 'x'` (the first unknown key in sorted order), `rule N: no condition` (none of payee, min_amount, max_amount), `rule N: min_amount must be a number` (likewise max_amount). Invalid TOML raises `tomllib.TOMLDecodeError`, itself a `ValueError`.
- A rule matches a transaction when every condition it has holds: `payee` is a case-insensitive substring of the payee as written; `min_amount <= amount`; `amount <= max_amount` (signed amounts).
- `apply_rules(txns, rules, overwrite: bool = False) -> list[Transaction]`: a new list in the same order. Each transaction whose category is `"uncategorized"` (every transaction, when `overwrite`) takes the category of the first rule that matches; otherwise it is unchanged.

## `ledger.dedupe`

Two transactions are the same when they have the same date, the same `normalize_payee` and the same amount.
- `find_duplicates(txns) -> list[list[Transaction]]`: every group of two or more same transactions, in input order inside a group; groups ordered by date, then normalized payee, then amount.
- `merge(*statements) -> list[Transaction]`: combines overlapping statements. For each distinct transaction, keep as many copies as the largest number of copies in any single statement (so an overlap counts once, but two identical purchases on one statement stay two). Copies are taken in order from the statements as given (the first statement first). The result is sorted by date, keeping that order among equal dates.

## `ledger.budget`

- `load_budgets(text: str) -> dict[str, Decimal]`: TOML with a table `budgets` of category to amount (number or numeric string); no table gives `{}`. Names are lower-cased and stripped; amounts go through `money`. An amount that is not a number or is not positive raises `ValueError("budget 'name': must be a positive amount")`, with the name as written.
- `BudgetLine`: a frozen dataclass `category: str`, `budget: Decimal`, `spent: Decimal`, `remaining: Decimal`, `status: str`.
- `budget_report(txns, budgets, month: str) -> list[BudgetLine]`: one line per budgeted category, ascending. `month` is `"YYYY-MM"`; anything else raises `ValueError`. `spent` is minus the sum of that category's amounts in that month (refunds reduce it and it may go negative); `remaining = budget - spent`; `status` is `"over"` when spent is more than the budget, `"warn"` when spent is at least 80% of it, else `"ok"`.

## `ledger.qif`

- `parse_qif(text: str, strict: bool = True) -> ParseResult`, with the same strict and lenient behaviour and the same `ParseError` as `parse_csv`.
- Lines are stripped; blank lines and lines starting with `!` are ignored. A line `^` ends a record; a last record without `^` still counts. Other lines are fields: the first character is the code and the rest the value. `D` date, `T` amount, `P` payee, `L` category; any other code is ignored; if a code repeats in a record, the first wins.
- `D` is month first: `M/D/YYYY` or `M/D'YY` (meaning 20YY); month and day may be one or two digits. `T` follows the CSV amount rules. `P` is stripped; empty is an error. `L` is lower-cased and stripped; empty or missing is `"uncategorized"`; a value starting with `[` (a transfer to an account) is `"transfer"`.
- Error lines: a record missing `D`, `T` or `P` reports the line of its first field (`missing date`, `missing amount`, `missing payee`, checked in that order); a bad field reports that field's line.

## `ledger.forecast`

- `project(txns, until: date) -> list[Transaction]`: future copies of every payment `find_recurring` finds. For each, the group's first transaction sets the anchor and its last transaction is where projection starts; copies fall strictly after the last transaction and on or before `until`. Weekly: every 7 days from the last. Monthly: each following month, on the first transaction's day of month, or the month's last day when it is shorter. Yearly: each following year, on the first transaction's month and day, clamped the same way. Each copy has the last transaction's payee (as written) and category, and the recurring amount. Sorted by date, then normalized payee.

## `ledger.export`

- `to_csv(txns) -> str`: a header `date,payee,amount,category`, then one row per transaction in order: ISO date, payee, amount as a plain two-decimal number, category; written with the `csv` module and `\n` line endings. `parse_csv(to_csv(txns)).transactions == txns` for any valid list.

## Command line

`python3 -m ledger FILE COMMAND [--json] [--as-of YYYY-MM-DD] [--lenient] [--rules FILE] [--also FILE ...] [--budgets FILE] [--month YYYY-MM] [--until YYYY-MM-DD]`, where `COMMAND` is `balance`, `categories`, `monthly`, `recurring`, `dupes`, `budget`, `forecast` or `export`.

A statement file whose name ends in `.qif` (any case) is read with `parse_qif`; any other with `parse_csv`. The steps run in this order: read `FILE`; merge in each `--also FILE` with `merge(main, *others)`; keep transactions on or before `--as-of`; apply `--rules` (without overwrite); run the command.

- `--as-of` keeps only transactions on or before the date, for every command.
- `--lenient` parses with `strict=False` and prints `skipped line N: message` to stderr for each skipped row; for a row in an `--also` file the message is `skipped PATH: line N: message`.
- `--rules FILE`: a rules file for `load_rules`.
- `--also FILE`: another statement to merge; repeatable.
- `balance` prints `Balance: 123.45`; with `--json`, `{"balance": "123.45"}`.
- `categories --json`: an object of category to amount, keys ascending.
- `monthly --json`: a list of `{"month", "income", "expense", "net"}` objects.
- `recurring --json`: a list of `{"payee", "amount", "interval", "count"}` objects (`count` an integer).
- `dupes --json`: a list of groups, each a list of `{"date", "payee", "amount", "category"}` objects (`date` ISO, `payee` as written).
- `budget` needs `--budgets FILE` and `--month YYYY-MM`; `--json`: a list of `{"category", "budget", "spent", "remaining", "status"}` objects.
- `forecast` needs `--until YYYY-MM-DD`; `--json`: a list of transaction objects as for `dupes`.
- `export` prints `to_csv` of the transactions exactly, whatever `--json` says.
- Text output for `categories`, `monthly`, `recurring`, `dupes`, `budget` and `forecast` is free, but must be readable and aligned.

Exit codes: 0 on success; 1 with `error: ...` on stderr when any file cannot be read, a date or month option is invalid, a rules or budgets file is invalid, or `budget` or `forecast` lacks its options; 2 on a parse error without `--lenient`, printing `line N: message` to stderr (`PATH: line N: message` for an `--also` file). Nothing goes to stdout on a failure.
