# TODO

Everything here must end up matching SPEC.md. Tests run with `python3 -m unittest discover -s tests`.

1. **Parsing.** `parse.py` only reads ISO dates and plain amounts, and raises a bare `ValueError`. Implement SPEC "ledger.parse" in full: the three date forms, the amount forms, `ParseError` with line numbers, `ParseResult`, strict and lenient modes, the header rules.
2. **Bug: balances are wrong.** Two reports from the user. (a) A ledger of `0.10` and `0.20` shows `Balance: 0.30000000000000004`. (b) `balance` with an as-of date of the 31st leaves out the transactions dated the 31st. Find both causes and fix them; money must follow SPEC "Money" everywhere.
3. **Reports.** Add `by_category` and `monthly` (SPEC "ledger.reports").
4. **Recurring payments.** Add `ledger/recurring.py` (SPEC "ledger.recurring").
5. **Command line.** Replace the stub in `__main__.py` with the full command line (SPEC "Command line").
6. **Tests.** Each of the above gets unit tests under `tests/`.
7. **README.** A usage section: each command with an example and its output, the flags, and the exit codes.
