# TODO

Everything here must end up matching SPEC.md. Tests run with `python3 -m unittest discover -s tests`.

1. **Parsing.** `rule.py` only reads `FREQ`, `INTERVAL`, `COUNT` and `UNTIL`, and accepts nonsense. Implement SPEC "recur.rule" in full, with every refusal.
2. **Bug: monthly rules crash.** `FREQ=MONTHLY` from January 31 raises `ValueError: day is out of range for month`. Find the cause and fix it as part of the expansion work.
3. **Expansion.** `expand.py` only steps days and weeks. Implement SPEC "recur.expand": periods and WKST, the defaults, every BY rule including ordinals, BYSETPOS, the bounds and the 400-year horizon. The RFC 5545 examples (section 3.8.5.3) are the check.
4. **Events.** Add `recur/ics.py` (SPEC "recur.ics").
5. **Command line.** Replace the stub in `__main__.py` (SPEC "Command line").
6. **Tests.** Each of the above gets unit tests under `tests/`.
7. **README.** A usage section: the supported RRULE subset, examples with output, the event format, and the exit codes.
