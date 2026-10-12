import json
import os
import subprocess
import sys
import tempfile
import unittest

CODE = os.environ.get("LEDGER_CODE_DIR", os.getcwd())
JAN = ("date,payee,amount,category\n"
       "2026-01-15,NETFLIX.COM 8842,-15.49,\n"
       "2026-01-20,Grocer,-120.00,\n"
       "2026-01-31,Employer,2000,salary\n")
FEB = ("date,payee,amount,category\n"
       "2026-01-31,Employer,2000,salary\n"
       "2026-02-15,Netflix.com 9911,-15.49,\n"
       "2026-02-16,Coffee,-3,\n"
       "2026-02-16,Coffee,-3,\n")
MAR_QIF = "!Type:Bank\nD03/15/2026\nT-15.49\nPnetflix.com\n^\nD03/20/2026\nT-60\nPGrocer\n^\n"
RULES = '[[rule]]\ncategory = "fun"\npayee = "netflix"\n[[rule]]\ncategory = "food"\npayee = "grocer"\n'
BUDGETS = '[budgets]\nfood = 100\nfun = 20\n'


def run(*args, files=None):
    files = {"jan.csv": JAN, "feb.csv": FEB, "mar.QIF": MAR_QIF, "rules.toml": RULES, "budgets.toml": BUDGETS, **(files or {})}
    with tempfile.TemporaryDirectory() as d:
        for name, text in files.items():
            with open(os.path.join(d, name), "w") as f:
                f.write(text)
        args = [a.replace("{d}", d) for a in args]
        p = subprocess.run([sys.executable, "-m", "ledger", *args], cwd=CODE, capture_output=True, text=True, timeout=60)
        return p.returncode, p.stdout, p.stderr.replace(d + os.sep, "")


class CliXL(unittest.TestCase):
    def test_merge_qif_and_rules(self):
        code, out, _ = run("{d}/jan.csv", "categories", "--json", "--also", "{d}/feb.csv", "--also", "{d}/mar.QIF",
                           "--rules", "{d}/rules.toml")
        self.assertEqual(code, 0)
        self.assertEqual(json.loads(out), {"food": "-180.00", "fun": "-46.47", "salary": "2000.00", "uncategorized": "-6.00"})

    def test_dupes_json(self):
        _, out, _ = run("{d}/feb.csv", "dupes", "--json")
        self.assertEqual(json.loads(out), [[{"date": "2026-02-16", "payee": "Coffee", "amount": "-3.00", "category": "uncategorized"}] * 2])

    def test_budget_json_and_missing_options(self):
        _, out, _ = run("{d}/jan.csv", "budget", "--json", "--budgets", "{d}/budgets.toml", "--month", "2026-01", "--rules", "{d}/rules.toml")
        self.assertEqual(json.loads(out), [{"category": "food", "budget": "100.00", "spent": "120.00", "remaining": "-20.00", "status": "over"},
                                           {"category": "fun", "budget": "20.00", "spent": "15.49", "remaining": "4.51", "status": "ok"}])
        code, out, err = run("{d}/jan.csv", "budget", "--month", "2026-01")
        self.assertEqual((code, out), (1, ""))
        self.assertTrue(err.startswith("error: "), err)

    def test_forecast_json(self):
        code, out, _ = run("{d}/jan.csv", "forecast", "--json", "--until", "2026-05-20", "--also", "{d}/feb.csv", "--also", "{d}/mar.QIF")
        self.assertEqual(code, 0)
        self.assertEqual(json.loads(out), [{"date": "2026-04-15", "payee": "netflix.com", "amount": "-15.49", "category": "uncategorized"},
                                           {"date": "2026-05-15", "payee": "netflix.com", "amount": "-15.49", "category": "uncategorized"}])
        code, _, err = run("{d}/jan.csv", "forecast")
        self.assertEqual(code, 1)
        self.assertTrue(err.startswith("error: "), err)

    def test_export_ignores_json(self):
        code, out, _ = run("{d}/feb.csv", "export", "--json", "--as-of", "2026-02-15")
        self.assertEqual((code, out), (0, "date,payee,amount,category\n2026-01-31,Employer,2000.00,salary\n2026-02-15,Netflix.com 9911,-15.49,uncategorized\n"))

    def test_also_parse_error_names_the_file(self):
        code, out, err = run("{d}/jan.csv", "balance", "--also", "{d}/bad.csv", files={"bad.csv": "date,payee,amount\n2026-01-01,x,oops\n"})
        self.assertEqual((code, out), (2, ""))
        self.assertTrue(err.strip().endswith("bad.csv: line 2: unrecognised amount 'oops'") or "bad.csv: line 2: " in err, err)

    def test_bad_rules_and_budgets_files_exit_1(self):
        # The spec does not say a budgets file is read by other commands, so each file goes to a command that uses it.
        for command, flag, name in (("balance", "--rules", "r.toml"), ("budget", "--budgets", "b.toml")):
            with self.subTest(flag=flag):
                code, out, err = run("{d}/jan.csv", command, flag, "{d}/" + name, "--month", "2026-01",
                                     files={"r.toml": '[[rule]]\npayee = "x"\n', "b.toml": "[budgets]\nfood = -1\n"})
                self.assertEqual((code, out), (1, ""))
                self.assertTrue(err.startswith("error: "), err)

    def test_no_negative_zero(self):
        _, out, _ = run("{d}/x.csv", "monthly", "--json", files={"x.csv": "date,payee,amount\n2026-01-01,A,5\n2026-03-01,B,-5\n"})
        rows = json.loads(out)
        self.assertEqual(rows[1], {"month": "2026-02", "income": "0.00", "expense": "0.00", "net": "0.00"})
        self.assertEqual(rows[0]["expense"], "0.00")
