import dataclasses
import unittest
from datetime import date
from decimal import Decimal

from ledger.model import Transaction, money
from ledger.parse import parse_csv
from ledger.reports import balance


class Money(unittest.TestCase):
    def test_no_float_error(self):
        r = parse_csv("date,payee,amount\n2026-01-01,A,0.10\n2026-01-02,B,0.20\n")
        self.assertEqual(str(balance(r.transactions)), "0.30")

    def test_as_of_is_inclusive(self):
        r = parse_csv("date,payee,amount\n2026-03-30,A,1\n2026-03-31,B,2\n2026-04-01,C,4\n")
        self.assertEqual(balance(r.transactions, as_of=date(2026, 3, 31)), Decimal("3.00"))

    def test_money_rounds_half_up(self):
        self.assertEqual(str(money(Decimal("2.345"))), "2.35")
        self.assertEqual(str(money(Decimal("-2.345"))), "-2.35")
        self.assertEqual(str(money(Decimal("2.5"))), "2.50")

    def test_transaction_shape(self):
        names = [f.name for f in dataclasses.fields(Transaction)]
        self.assertEqual(names, ["date", "payee", "amount", "category"])
        t = Transaction(date(2026, 1, 1), "A", Decimal("1.00"))
        self.assertEqual(t.category, "uncategorized")
        with self.assertRaises(dataclasses.FrozenInstanceError):
            t.payee = "B"

    def test_large_sum_exact(self):
        rows = "".join(f"2026-01-01,P{i},0.01\n" for i in range(1000))
        r = parse_csv("date,payee,amount\n" + rows)
        self.assertEqual(str(balance(r.transactions)), "10.00")
