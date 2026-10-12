import unittest
from datetime import date
from decimal import Decimal

from ledger.model import Transaction
from ledger.reports import MonthRow, balance, by_category, monthly


def t(d, a, c="uncategorized", p="P"):
    return Transaction(date.fromisoformat(d), p, Decimal(a), c)


class Reports(unittest.TestCase):
    def test_balance_all_and_empty(self):
        self.assertEqual(balance([t("2026-01-01", "1.50"), t("2026-02-01", "-0.25")]), Decimal("1.25"))
        self.assertEqual(str(balance([])), "0.00")

    def test_by_category_sorted_totals(self):
        got = by_category([t("2026-01-01", "-5", "groceries"), t("2026-01-02", "100", "salary"),
                           t("2026-01-03", "-2.5", "groceries"), t("2026-01-04", "-1", "books")])
        self.assertEqual(list(got), ["books", "groceries", "salary"])
        self.assertEqual({k: str(v) for k, v in got.items()},
                         {"books": "-1.00", "groceries": "-7.50", "salary": "100.00"})

    def test_monthly_fills_gaps(self):
        rows = monthly([t("2025-11-15", "10"), t("2026-02-01", "-4"), t("2026-02-20", "6")])
        self.assertEqual([r.month for r in rows], ["2025-11", "2025-12", "2026-01", "2026-02"])
        self.assertEqual(rows[1], MonthRow("2025-12", Decimal("0.00"), Decimal("0.00"), Decimal("0.00")))
        last = rows[-1]
        self.assertEqual((str(last.income), str(last.expense), str(last.net)), ("6.00", "4.00", "2.00"))

    def test_monthly_empty(self):
        self.assertEqual(monthly([]), [])

    def test_monthly_single_month(self):
        rows = monthly([t("2026-05-31", "-3.333"), t("2026-05-01", "1")])
        self.assertEqual(len(rows), 1)
        self.assertEqual(str(rows[0].expense), "3.33")

    def test_month_row_is_frozen_dataclass(self):
        r = MonthRow("2026-01", Decimal(0), Decimal(0), Decimal(0))
        with self.assertRaises(Exception):
            r.month = "x"

    def test_unsorted_input(self):
        rows = monthly([t("2026-03-01", "1"), t("2026-01-01", "1")])
        self.assertEqual([r.month for r in rows], ["2026-01", "2026-02", "2026-03"])
