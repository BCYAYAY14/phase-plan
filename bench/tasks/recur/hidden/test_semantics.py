import unittest
from datetime import date

from recur.expand import occurrences
from recur.rule import parse_rrule


def run(rule, start, end=None, limit=None):
    return occurrences(parse_rrule(rule), start, end=end, limit=limit)


class Semantics(unittest.TestCase):
    def test_start_not_matching_is_not_an_occurrence(self):
        self.assertEqual(run("FREQ=WEEKLY;BYDAY=MO;COUNT=2", date(2026, 1, 6)), [date(2026, 1, 12), date(2026, 1, 19)])

    def test_monthly_31st_skips_short_months(self):
        self.assertEqual(run("FREQ=MONTHLY;COUNT=4", date(2026, 1, 31)),
                         [date(2026, 1, 31), date(2026, 3, 31), date(2026, 5, 31), date(2026, 7, 31)])

    def test_yearly_leap_day(self):
        self.assertEqual(run("FREQ=YEARLY;COUNT=3", date(2024, 2, 29)), [date(2024, 2, 29), date(2028, 2, 29), date(2032, 2, 29)])

    def test_unbounded_needs_a_bound(self):
        with self.assertRaises(ValueError):
            run("FREQ=DAILY", date(2026, 1, 1))
        self.assertEqual(len(run("FREQ=DAILY", date(2026, 1, 1), limit=3)), 3)

    def test_end_and_until_are_inclusive_and_the_earlier_wins(self):
        self.assertEqual(run("FREQ=DAILY;UNTIL=20260105", date(2026, 1, 1), end=date(2026, 1, 3))[-1], date(2026, 1, 3))
        self.assertEqual(run("FREQ=DAILY;UNTIL=20260103", date(2026, 1, 1), end=date(2026, 1, 9))[-1], date(2026, 1, 3))

    def test_count_counts_from_the_first_produced(self):
        self.assertEqual(run("FREQ=MONTHLY;BYDAY=-1FR;COUNT=2", date(2026, 1, 31)), [date(2026, 2, 27), date(2026, 3, 27)])

    def test_impossible_rule_ends(self):
        self.assertEqual(run("FREQ=YEARLY;BYMONTH=2;BYMONTHDAY=30", date(2026, 1, 1), limit=5), [])

    def test_negative_yearday_and_setpos_on_yearly(self):
        self.assertEqual(run("FREQ=YEARLY;BYYEARDAY=-1;COUNT=2", date(2026, 6, 1)), [date(2026, 12, 31), date(2027, 12, 31)])
        self.assertEqual(run("FREQ=YEARLY;BYMONTH=1,7;BYDAY=MO;BYSETPOS=1,-1;COUNT=4", date(2026, 1, 1)),
                         [date(2026, 1, 5), date(2026, 7, 27), date(2027, 1, 4), date(2027, 7, 26)])

    def test_yearly_ordinal_inside_month_when_bymonth(self):
        self.assertEqual(run("FREQ=YEARLY;BYMONTH=11;BYDAY=4TH;COUNT=2", date(2026, 1, 1)), [date(2026, 11, 26), date(2027, 11, 25)])

    def test_daily_byday_filters(self):
        self.assertEqual(run("FREQ=DAILY;BYDAY=SA,SU;COUNT=3", date(2026, 1, 1)), [date(2026, 1, 3), date(2026, 1, 4), date(2026, 1, 10)])

    def test_weekly_wkst_default_monday(self):
        self.assertEqual(run("FREQ=WEEKLY;INTERVAL=2;BYDAY=SU,TU;COUNT=3", date(2026, 1, 6)),
                         [date(2026, 1, 6), date(2026, 1, 11), date(2026, 1, 20)])
