import unittest
from datetime import date
from decimal import Decimal

from ledger.export import to_csv
from ledger.model import Transaction
from ledger.parse import parse_csv


class Export(unittest.TestCase):
    def test_exact_text(self):
        txns = [Transaction(date(2026, 1, 2), "Shop, Inc", Decimal("-5.00"), "food"),
                Transaction(date(2026, 1, 3), "Pay", Decimal("1000.00"))]
        self.assertEqual(to_csv(txns), 'date,payee,amount,category\n2026-01-02,"Shop, Inc",-5.00,food\n'
                                       '2026-01-03,Pay,1000.00,uncategorized\n')

    def test_round_trip(self):
        txns = [Transaction(date(2026, 1, 2), 'Say "hi"', Decimal("-0.01"), "x"),
                Transaction(date(2025, 12, 31), "Line\\nbreak", Decimal("12.30"), "y")]
        self.assertEqual(parse_csv(to_csv(txns)).transactions, txns)

    def test_empty(self):
        self.assertEqual(to_csv([]), "date,payee,amount,category\n")
