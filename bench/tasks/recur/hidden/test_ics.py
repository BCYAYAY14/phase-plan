import unittest
from datetime import date

from recur.ics import event_dates

EVENT = """BEGIN:VCALENDAR\r
BEGIN:VEVENT\r
SUMMARY:Book club\r
DTSTART;VALUE=DATE:20260106\r
RRULE:FREQ=MONTHLY;BYDAY=1T\r
 U\r
EXDATE;VALUE=DATE:20260303,20260407\r
EXDATE;VALUE=DATE:20260505\r
RDATE;VALUE=DATE:20260318\r
END:VEVENT\r
END:VCALENDAR\r
"""


class Ics(unittest.TestCase):
    def test_rule_folding_exdates_rdates(self):
        self.assertEqual(event_dates(EVENT, date(2026, 6, 30)),
                         [date(2026, 1, 6), date(2026, 2, 3), date(2026, 3, 18), date(2026, 6, 2)])

    def test_dtstart_always_counts_and_no_rule(self):
        self.assertEqual(event_dates("DTSTART;VALUE=DATE:20260107\nRRULE:FREQ=WEEKLY;BYDAY=MO;COUNT=2\n", date(2026, 12, 31)),
                         [date(2026, 1, 7), date(2026, 1, 12), date(2026, 1, 19)])
        self.assertEqual(event_dates("DTSTART:20260107\n", date(2026, 12, 31)), [date(2026, 1, 7)])

    def test_end_bounds_everything_and_duplicates_merge(self):
        text = "DTSTART;VALUE=DATE:20260101\nRRULE:FREQ=DAILY\nRDATE;VALUE=DATE:20260102,20270101\n"
        self.assertEqual(event_dates(text, date(2026, 1, 3)), [date(2026, 1, 1), date(2026, 1, 2), date(2026, 1, 3)])

    def test_errors(self):
        for text in ("RRULE:FREQ=DAILY;COUNT=2\n", "DTSTART;VALUE=DATE:2026011\n", "DTSTART:20260101\nRRULE:FREQ=SECONDLY\n",
                     "DTSTART:20260101\nEXDATE:20261301\n"):
            with self.subTest(text=text), self.assertRaises(ValueError):
                event_dates(text, date(2026, 12, 31))
