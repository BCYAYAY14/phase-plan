import unittest
from datetime import date, timedelta
from decimal import Decimal

from ledger.model import Transaction
from ledger.recurring import Recurring, find_recurring, normalize_payee


def series(payee, start, step, amounts):
    d = date.fromisoformat(start)
    out = []
    for i, a in enumerate(amounts):
        out.append(Transaction(d + timedelta(days=step * i), payee, Decimal(a), "x"))
    return out


class Normalize(unittest.TestCase):
    def test_examples(self):
        self.assertEqual(normalize_payee("NETFLIX.COM 8842"), "netflix.com")
        self.assertEqual(normalize_payee("Spotify  #1234"), "spotify")
        self.assertEqual(normalize_payee("7-Eleven"), "7-eleven")
        self.assertEqual(normalize_payee("Gym Co 22 ref9"), "gym co")
        self.assertEqual(normalize_payee("  Corner   Shop "), "corner shop")


class Find(unittest.TestCase):
    def test_monthly_with_varied_payee_refs(self):
        txns = [Transaction(date(2026, 1, 15), "NETFLIX.COM 8842", Decimal("-15.49"), "x"),
                Transaction(date(2026, 2, 15), "Netflix.com 9911", Decimal("-15.49"), "x"),
                Transaction(date(2026, 3, 15), "netflix.com", Decimal("-15.49"), "x")]
        self.assertEqual(find_recurring(txns), [Recurring("netflix.com", Decimal("-15.49"), "monthly", 3)])

    def test_weekly_and_yearly(self):
        txns = series("Cleaner", "2026-01-02", 7, ["-40"] * 4) + series("Insurance", "2023-06-01", 365, ["-300"] * 3)
        got = find_recurring(txns)
        self.assertEqual([(r.payee, r.interval, r.count) for r in got], [("cleaner", "weekly", 4), ("insurance", "yearly", 3)])

    def test_two_is_not_enough(self):
        self.assertEqual(find_recurring(series("Gym", "2026-01-01", 30, ["-20", "-20"])), [])

    def test_amount_outside_five_percent(self):
        self.assertEqual(find_recurring(series("Gym", "2026-01-01", 30, ["-20", "-20", "-21.50"])), [])

    def test_amount_at_five_percent_boundary(self):
        got = find_recurring(series("Gym", "2026-01-01", 30, ["-20", "-20", "-21"]))
        self.assertEqual(got, [Recurring("gym", Decimal("-20.00"), "monthly", 3)])

    def test_mixed_gaps_are_not_recurring(self):
        txns = (series("A", "2026-01-01", 7, ["-1", "-1"]) + series("A", "2026-02-01", 30, ["-1", "-1"]))
        self.assertEqual(find_recurring(txns), [])

    def test_february_gap_and_even_median(self):
        txns = [Transaction(date(2026, 1, 31), "Rent", Decimal("-1000"), "x"),
                Transaction(date(2026, 2, 28), "Rent", Decimal("-1010"), "x"),
                Transaction(date(2026, 3, 31), "Rent", Decimal("-1020"), "x"),
                Transaction(date(2026, 4, 30), "Rent", Decimal("-1030"), "x")]
        self.assertEqual(find_recurring(txns), [Recurring("rent", Decimal("-1015.00"), "monthly", 4)])

    def test_unsorted_input_and_sorted_output(self):
        txns = series("Zeta", "2026-01-01", 30, ["-5"] * 3) + series("Alpha", "2026-01-01", 30, ["9"] * 3)
        got = find_recurring(list(reversed(txns)))
        self.assertEqual([r.payee for r in got], ["alpha", "zeta"])
        self.assertEqual(got[0].amount, Decimal("9.00"))
