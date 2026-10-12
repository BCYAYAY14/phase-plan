import unittest
from datetime import date

from ledger.parse import parse_csv
from ledger.reports import balance

CSV = "date,payee,amount,category\n2026-01-02,Bakery,-4.50,Food\n2026-01-03,Employer,100,Salary\n"


class Basic(unittest.TestCase):
    def test_parses_iso_rows(self):
        txns = parse_csv(CSV)
        self.assertEqual(len(txns), 2)
        self.assertEqual(txns[0].date, date(2026, 1, 2))
        self.assertEqual(txns[0].category, "food")

    def test_balance(self):
        self.assertEqual(balance(parse_csv(CSV)), 95.5)


if __name__ == "__main__":
    unittest.main()
