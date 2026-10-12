import unittest
from datetime import date, timedelta
from decimal import Decimal

from ledger.forecast import project
from ledger.model import Transaction


def tx(d, payee, amount, category="bills"):
    return Transaction(d if isinstance(d, date) else date.fromisoformat(d), payee, Decimal(amount), category)


class Forecast(unittest.TestCase):
    def test_monthly_clamps_to_month_end_from_first_day(self):
        txns = [tx("2026-01-31", "Rent", "-1000"), tx("2026-02-28", "Rent", "-1000"), tx("2026-03-31", "RENT", "-1000", "home")]
        got = project(txns, date(2026, 6, 30))
        self.assertEqual([(x.date, x.payee, str(x.amount), x.category) for x in got],
                         [(date(2026, 4, 30), "RENT", "-1000.00", "home"), (date(2026, 5, 31), "RENT", "-1000.00", "home"),
                          (date(2026, 6, 30), "RENT", "-1000.00", "home")])

    def test_weekly_until_inclusive(self):
        start = date(2026, 1, 2)
        txns = [tx(start + timedelta(days=7 * i), "Cleaner", "-40") for i in range(3)]
        got = project(txns, date(2026, 1, 30))
        self.assertEqual([x.date for x in got], [date(2026, 1, 23), date(2026, 1, 30)])

    def test_yearly_leap_day(self):
        txns = [tx("2024-02-29", "Insurance", "-300"), tx("2025-02-28", "Insurance", "-300"), tx("2026-02-28", "Insurance", "-300")]
        got = project(txns, date(2029, 1, 1))
        self.assertEqual([x.date for x in got], [date(2027, 2, 28), date(2028, 2, 29)])

    def test_year_rollover_and_sorting(self):
        txns = ([tx(f"2025-{m:02d}-15", "Zeta", "-5") for m in (10, 11, 12)]
                + [tx(f"2025-{m:02d}-15", "Alpha", "-9") for m in (10, 11, 12)])
        got = project(txns, date(2026, 2, 15))
        self.assertEqual([(x.date, x.payee) for x in got],
                         [(date(2026, 1, 15), "Alpha"), (date(2026, 1, 15), "Zeta"),
                          (date(2026, 2, 15), "Alpha"), (date(2026, 2, 15), "Zeta")])

    def test_nothing_before_last_or_without_recurring(self):
        txns = [tx("2026-01-15", "Gym", "-20"), tx("2026-02-15", "Gym", "-20"), tx("2026-03-15", "Gym", "-20")]
        self.assertEqual(project(txns, date(2026, 3, 15)), [])
        self.assertEqual(project(txns[:2], date(2027, 1, 1)), [])

    def test_amount_is_the_median(self):
        txns = [tx("2026-01-10", "Power", "-100"), tx("2026-02-10", "Power", "-104"), tx("2026-03-10", "Power", "-102")]
        self.assertEqual(str(project(txns, date(2026, 4, 10))[0].amount), "-102.00")
