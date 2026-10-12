import unittest
from datetime import date

from ledger.parse import ParseError
from ledger.qif import parse_qif

QIF = """!Type:Bank
D03/05/2026
T-15.49
PNetflix
LFun
MMemo ignored
^
D3/6'26
T1,000.00
P Employer
^
D03/07/2026
T-200
PTransfer out
L[Savings]
^
D03/08/2026
T(4.50)
PBakery
"""


class Qif(unittest.TestCase):
    def test_reads_records(self):
        txns = parse_qif(QIF).transactions
        self.assertEqual([(x.date, x.payee, str(x.amount), x.category) for x in txns],
                         [(date(2026, 3, 5), "Netflix", "-15.49", "fun"),
                          (date(2026, 3, 6), "Employer", "1000.00", "uncategorized"),
                          (date(2026, 3, 7), "Transfer out", "-200.00", "transfer"),
                          (date(2026, 3, 8), "Bakery", "-4.50", "uncategorized")])

    def test_first_code_wins(self):
        txns = parse_qif("D01/02/2026\nT1\nPFirst\nPSecond\n^\n").transactions
        self.assertEqual(txns[0].payee, "First")

    def test_missing_field_reports_first_line(self):
        with self.assertRaises(ParseError) as cm:
            parse_qif("!Type:Bank\n\nT5\nPShop\n^\n")
        self.assertEqual((cm.exception.line, cm.exception.message), (3, "missing date"))

    def test_bad_field_reports_its_line(self):
        with self.assertRaises(ParseError) as cm:
            parse_qif("D01/02/2026\nT5\nPShop\n^\nD02/30/2026\nT1\nPx\n^\n")
        self.assertEqual(cm.exception.line, 5)
        with self.assertRaises(ParseError) as cm:
            parse_qif("D01/02/2026\nPShop\nT1.234\n^\n")
        self.assertEqual(cm.exception.line, 3)

    def test_day_first_is_not_accepted_as_written(self):
        with self.assertRaises(ParseError):
            parse_qif("D2026-01-02\nT1\nPx\n^\n")

    def test_lenient(self):
        r = parse_qif("D01/02/2026\nT1\nPA\n^\nT2\nPB\n^\nD01/04/2026\nT3\nPC\n^\n", strict=False)
        self.assertEqual([x.payee for x in r.transactions], ["A", "C"])
        self.assertEqual([(e.line, e.message) for e in r.errors], [(5, "missing date")])

    def test_empty_payee(self):
        with self.assertRaises(ParseError) as cm:
            parse_qif("D01/02/2026\nT1\nP   \n^\n")
        self.assertEqual(cm.exception.line, 3)
