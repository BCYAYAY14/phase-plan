import unittest
from datetime import date

from recur.expand import occurrences
from recur.rule import parse_rrule


class Basic(unittest.TestCase):
    def test_daily_count(self):
        self.assertEqual(occurrences(parse_rrule("FREQ=DAILY;COUNT=3"), date(2026, 1, 1)),
                         [date(2026, 1, 1), date(2026, 1, 2), date(2026, 1, 3)])

    def test_weekly_interval(self):
        self.assertEqual(occurrences(parse_rrule("FREQ=WEEKLY;INTERVAL=2;COUNT=2"), date(2026, 1, 1)),
                         [date(2026, 1, 1), date(2026, 1, 15)])


if __name__ == "__main__":
    unittest.main()
