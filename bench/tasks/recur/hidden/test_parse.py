import unittest
from datetime import date

from recur.rule import Rule, parse_rrule


class Parse(unittest.TestCase):
    def test_full_rule(self):
        r = parse_rrule("RRULE:FREQ=MONTHLY;INTERVAL=2;COUNT=10;BYDAY=1SU,-1SU,MO;BYMONTH=1,12;BYSETPOS=-1;WKST=SU")
        self.assertEqual(r, Rule("MONTHLY", 2, 10, None, (1, 12), (), (), ((1, 6), (-1, 6), (0, 0)), (-1,), 6))

    def test_case_order_and_until(self):
        r = parse_rrule("until=20261231T235959Z;freq=yearly;bymonthday=-1;byyearday=1,-366")
        self.assertEqual((r.freq, r.until, r.bymonthday, r.byyearday, r.interval, r.wkst), ("YEARLY", date(2026, 12, 31), (-1,), (1, -366), 1, 0))
        self.assertEqual(parse_rrule("FREQ=DAILY;UNTIL=20260102").until, date(2026, 1, 2))

    def test_errors(self):
        bad = ["", "COUNT=3", "FREQ=HOURLY", "FREQ=DAILY;FREQ=DAILY", "FREQ=DAILY;FOO=1", "FREQ=DAILY;COUNT=2;UNTIL=20260101",
               "FREQ=DAILY;INTERVAL=0", "FREQ=DAILY;COUNT=0", "FREQ=DAILY;COUNT=x", "FREQ=YEARLY;BYMONTH=13", "FREQ=YEARLY;BYMONTH=-1",
               "FREQ=MONTHLY;BYMONTHDAY=0", "FREQ=MONTHLY;BYMONTHDAY=32", "FREQ=YEARLY;BYYEARDAY=367", "FREQ=MONTHLY;BYDAY=XX",
               "FREQ=MONTHLY;BYDAY=0MO", "FREQ=MONTHLY;BYDAY=54MO", "FREQ=WEEKLY;BYDAY=1MO", "FREQ=DAILY;BYDAY=-1FR",
               "FREQ=WEEKLY;BYMONTHDAY=1", "FREQ=MONTHLY;BYYEARDAY=1", "FREQ=MONTHLY;BYSETPOS=1", "FREQ=DAILY;UNTIL=20260230",
               "FREQ=DAILY;WKST=XY", "FREQ=DAILY;COUNT"]
        for text in bad:
            with self.subTest(text=text), self.assertRaises(ValueError):
                parse_rrule(text)

    def test_rule_defaults(self):
        self.assertEqual(Rule("DAILY"), Rule("DAILY", 1, None, None, (), (), (), (), (), 0))
