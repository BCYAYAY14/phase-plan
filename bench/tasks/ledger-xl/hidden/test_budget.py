import unittest
from datetime import date
from decimal import Decimal

from ledger.budget import BudgetLine, budget_report, load_budgets
from ledger.model import Transaction


def t(d, amount, category):
    return Transaction(date.fromisoformat(d), "P", Decimal(amount), category)


class Load(unittest.TestCase):
    def test_loads(self):
        self.assertEqual(load_budgets('[budgets]\n" Food " = 200\nfun = "50.5"\n'),
                         {"food": Decimal("200.00"), "fun": Decimal("50.50")})
        self.assertEqual(load_budgets(""), {})

    def test_errors(self):
        for text, name in (('[budgets]\nFood = 0\n', "Food"), ('[budgets]\nrent = -5\n', "rent"),
                           ('[budgets]\nfun = "lots"\n', "fun"), ('[budgets]\nfun = true\n', "fun")):
            with self.subTest(text=text), self.assertRaises(ValueError) as cm:
                load_budgets(text)
            self.assertEqual(str(cm.exception), f"budget '{name}': must be a positive amount")


class Report(unittest.TestCase):
    TX = [t("2026-03-01", "-150", "food"), t("2026-03-15", "-30", "food"), t("2026-03-20", "20", "food"),
          t("2026-03-02", "-40", "fun"), t("2026-02-28", "-500", "fun"), t("2026-03-03", "-60", "rent")]

    def test_statuses(self):
        got = budget_report(self.TX, {"food": Decimal("200"), "fun": Decimal("50"), "rent": Decimal("50"),
                                      "books": Decimal("10")}, "2026-03")
        self.assertEqual([(b.category, str(b.spent), str(b.remaining), b.status) for b in got],
                         [("books", "0.00", "10.00", "ok"), ("food", "160.00", "40.00", "warn"),
                          ("fun", "40.00", "10.00", "warn"), ("rent", "60.00", "-10.00", "over")])
        self.assertIsInstance(got[0], BudgetLine)

    def test_refunds_can_make_spent_negative(self):
        got = budget_report([t("2026-03-01", "25", "fun")], {"fun": Decimal("50")}, "2026-03")
        self.assertEqual((str(got[0].spent), str(got[0].remaining), got[0].status), ("-25.00", "75.00", "ok"))

    def test_bad_month(self):
        for month in ("2026-3", "2026-13", "March"):
            with self.subTest(month=month), self.assertRaises(ValueError):
                budget_report([], {"a": Decimal("1")}, month)
