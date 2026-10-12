import unittest
from datetime import date
from decimal import Decimal

from ledger.model import Transaction
from ledger.rules import Rule, apply_rules, load_rules


def t(payee, amount, category="uncategorized"):
    return Transaction(date(2026, 1, 1), payee, Decimal(amount), category)


class Load(unittest.TestCase):
    def test_loads_all_keys(self):
        rules = load_rules('[[rule]]\ncategory = " Food "\npayee = "Grocer"\nmin_amount = -100\nmax_amount = "-0.5"\n'
                           '[[rule]]\ncategory = "fun"\npayee = "netflix"\n')
        self.assertEqual(rules[0], Rule("food", "Grocer", Decimal("-100.00"), Decimal("-0.50")))
        self.assertEqual(rules[1], Rule("fun", "netflix"))

    def test_empty(self):
        self.assertEqual(load_rules(""), [])

    def test_errors(self):
        cases = {'[[rule]]\npayee = "x"\n': "rule 1: missing category",
                 '[[rule]]\ncategory = "a"\npayee = "x"\n[[rule]]\ncategory = "b"\n': "rule 2: no condition",
                 '[[rule]]\ncategory = "a"\nzeta = 1\nalpha = 2\n': "rule 1: unknown key 'alpha'",
                 '[[rule]]\ncategory = "a"\nmin_amount = "lots"\n': "rule 1: min_amount must be a number"}
        for text, message in cases.items():
            with self.subTest(message=message), self.assertRaises(ValueError) as cm:
                load_rules(text)
            self.assertEqual(str(cm.exception), message)

    def test_bad_toml_is_value_error(self):
        with self.assertRaises(ValueError):
            load_rules("[[rule]\n")


class Apply(unittest.TestCase):
    def test_first_match_wins_and_conditions_combine(self):
        rules = [Rule("big", payee="shop", max_amount=Decimal("-100")), Rule("shopping", payee="SHOP")]
        got = apply_rules([t("Corner Shop", "-150"), t("Corner Shop", "-5"), t("Bakery", "-5")], rules)
        self.assertEqual([x.category for x in got], ["big", "shopping", "uncategorized"])

    def test_only_uncategorized_unless_overwrite(self):
        rules = [Rule("fun", payee="netflix")]
        txns = [t("Netflix", "-15", "subscriptions")]
        self.assertEqual(apply_rules(txns, rules)[0].category, "subscriptions")
        self.assertEqual(apply_rules(txns, rules, overwrite=True)[0].category, "fun")

    def test_amount_bounds_inclusive_and_input_untouched(self):
        txns = [t("A", "10"), t("A", "20"), t("A", "20.01")]
        got = apply_rules(txns, [Rule("mid", min_amount=Decimal("10"), max_amount=Decimal("20"))])
        self.assertEqual([x.category for x in got], ["mid", "mid", "uncategorized"])
        self.assertEqual(txns[0].category, "uncategorized")
