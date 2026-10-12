import unittest
from datetime import date
from decimal import Decimal

from ledger.dedupe import find_duplicates, merge
from ledger.model import Transaction


def t(d, payee, amount, category="x"):
    return Transaction(date.fromisoformat(d), payee, Decimal(amount), category)


class Dupes(unittest.TestCase):
    def test_groups_by_normalized_payee(self):
        a, b = t("2026-01-02", "NETFLIX.COM 8842", "-15.49"), t("2026-01-02", "Netflix.com 9911", "-15.49")
        c = t("2026-01-02", "Netflix.com", "-15.50")
        self.assertEqual(find_duplicates([a, c, b]), [[a, b]])

    def test_group_order(self):
        x1, x2 = t("2026-01-05", "Zed", "-1"), t("2026-01-05", "Zed", "-1")
        y1, y2 = t("2026-01-05", "Abe", "-2"), t("2026-01-05", "Abe", "-2")
        z1, z2 = t("2026-01-01", "Zed", "-1"), t("2026-01-01", "Zed", "-1")
        w1, w2 = t("2026-01-05", "Abe", "-3"), t("2026-01-05", "Abe", "-3")
        got = find_duplicates([x1, y1, z1, w1, x2, y2, z2, w2])
        self.assertEqual(got, [[z1, z2], [w1, w2], [y1, y2], [x1, x2]])

    def test_none(self):
        self.assertEqual(find_duplicates([t("2026-01-01", "A", "1")]), [])


class Merge(unittest.TestCase):
    def test_overlap_counted_once(self):
        jan = [t("2026-01-30", "A", "-1"), t("2026-01-31", "B", "-2")]
        feb = [t("2026-01-31", "B", "-2"), t("2026-02-01", "C", "-3")]
        self.assertEqual([x.payee for x in merge(jan, feb)], ["A", "B", "C"])

    def test_keeps_genuine_repeats(self):
        one = [t("2026-01-31", "Coffee", "-3"), t("2026-01-31", "Coffee", "-3")]
        two = [t("2026-01-31", "coffee", "-3")]
        self.assertEqual(len(merge(one, two)), 2)
        self.assertEqual(len(merge(two, one)), 2)

    def test_first_copies_win_and_sorted_stably(self):
        a = t("2026-01-02", "Shop", "-5", "first")
        b = t("2026-01-02", "SHOP", "-5", "second")
        c = t("2026-01-01", "Early", "-1")
        d = t("2026-01-02", "Other", "-9")
        got = merge([a, d], [c, b])
        self.assertEqual(got, [c, a, d])

    def test_no_statements(self):
        self.assertEqual(merge(), [])
