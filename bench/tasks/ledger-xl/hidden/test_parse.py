import unittest
from datetime import date
from decimal import Decimal

from ledger.parse import ParseError, ParseResult, parse_csv

H = "date,payee,amount,category\n"


def one(row, header=H):
    return parse_csv(header + row + "\n").transactions[0]


class Dates(unittest.TestCase):
    def test_iso(self):
        self.assertEqual(one("2026-03-05,A,1,x").date, date(2026, 3, 5))

    def test_day_first_slash(self):
        self.assertEqual(one("05/03/2026,A,1,x").date, date(2026, 3, 5))
        self.assertEqual(one("5/3/2026,A,1,x").date, date(2026, 3, 5))

    def test_month_names(self):
        self.assertEqual(one('"Mar 5, 2026",A,1,x').date, date(2026, 3, 5))
        self.assertEqual(one('"march 05, 2026",A,1,x').date, date(2026, 3, 5))
        self.assertEqual(one('"DEC 31, 2025",A,1,x').date, date(2025, 12, 31))

    def test_impossible_date_is_an_error(self):
        with self.assertRaises(ParseError) as cm:
            parse_csv(H + "2026-02-30,A,1,x\n")
        self.assertEqual(cm.exception.line, 2)

    def test_other_forms_are_errors(self):
        for bad in ("2026/03/05", "03-05-2026", "Mars 5, 2026", ""):
            with self.subTest(bad=bad), self.assertRaises(ParseError):
                parse_csv(H + f'"{bad}",A,1,x\n')


class Amounts(unittest.TestCase):
    def test_forms(self):
        cases = {"12": "12.00", '"1,234.56"': "1234.56", "-$5.00": "-5.00", '"($1,000.10)"': "-1000.10",
                 "€3.5": "3.50", "£0.99": "0.99", "(7)": "-7.00"}
        for raw, want in cases.items():
            with self.subTest(raw=raw):
                a = one(f"2026-01-01,A,{raw},x").amount
                self.assertIsInstance(a, Decimal)
                self.assertEqual(str(a), want)

    def test_errors(self):
        for bad in ("1.234", "", "abc", "-(5)", "5-", "$", "1.2.3"):
            with self.subTest(bad=bad), self.assertRaises(ParseError):
                parse_csv(H + f'2026-01-01,A,"{bad}",x\n')


class Rows(unittest.TestCase):
    def test_header_any_case_order_and_extra_columns(self):
        r = parse_csv(" Amount ,Memo,PAYEE,Date\n-3,hi,Shop,2026-01-01\n")
        t = r.transactions[0]
        self.assertEqual((t.payee, str(t.amount), t.date, t.category), ("Shop", "-3.00", date(2026, 1, 1), "uncategorized"))

    def test_missing_column_raises_even_when_lenient(self):
        for strict in (True, False):
            with self.subTest(strict=strict), self.assertRaises(ParseError) as cm:
                parse_csv("\ndate,amount\n2026-01-01,1\n", strict=strict)
            self.assertEqual(cm.exception.line, 2)

    def test_blank_rows_skipped_and_line_numbers_physical(self):
        text = H + "\n2026-01-01,A,1,x\n , , , \n2026-01-02,B,bad,x\n"
        with self.assertRaises(ParseError) as cm:
            parse_csv(text)
        self.assertEqual(cm.exception.line, 5)
        self.assertEqual(str(cm.exception), f"line 5: {cm.exception.message}")

    def test_quoted_multiline_field_counts_physical_lines(self):
        text = H + '2026-01-01,"Two\nlines",1,x\n2026-01-02,B,bad,x\n'
        with self.assertRaises(ParseError) as cm:
            parse_csv(text)
        self.assertEqual(cm.exception.line, 4)

    def test_payee_and_category(self):
        t = one("2026-01-01,  Corner Shop  ,1,  Food ")
        self.assertEqual((t.payee, t.category), ("Corner Shop", "food"))
        self.assertEqual(one("2026-01-01,A,1,").category, "uncategorized")
        self.assertEqual(parse_csv("date,payee,amount\n2026-01-01,A,1\n").transactions[0].category, "uncategorized")

    def test_empty_payee_is_an_error(self):
        with self.assertRaises(ParseError):
            parse_csv(H + "2026-01-01,  ,1,x\n")

    def test_lenient_collects_errors_in_order(self):
        text = H + "2026-01-01,A,1,x\nnope,B,1,x\n2026-01-03,C,1,x\n2026-01-04,D,x,x\n"
        r = parse_csv(text, strict=False)
        self.assertIsInstance(r, ParseResult)
        self.assertEqual([t.payee for t in r.transactions], ["A", "C"])
        self.assertEqual([e.line for e in r.errors], [3, 5])
        self.assertTrue(all(isinstance(e, ParseError) for e in r.errors))

    def test_strict_is_default(self):
        with self.assertRaises(ParseError):
            parse_csv(H + "nope,B,1,x\n")
