import json
import os
import subprocess
import sys
import tempfile
import unittest

CODE = os.environ.get("LEDGER_CODE_DIR", os.getcwd())
CSV = ("date,payee,amount,category\n"
       "2026-01-15,NETFLIX.COM 8842,-15.49,fun\n"
       "2026-01-31,Employer,2000,salary\n"
       "2026-02-15,Netflix.com 9911,-15.49,fun\n"
       "2026-03-15,netflix.com,-15.49,fun\n"
       "2026-03-31,Grocer,-80.10,food\n")


def run(*args, text=CSV):
    with tempfile.TemporaryDirectory() as d:
        path = os.path.join(d, "s.csv")
        with open(path, "w") as f:
            f.write(text)
        args = [a.replace("{file}", path) for a in args]
        p = subprocess.run([sys.executable, "-m", "ledger", *args], cwd=CODE, capture_output=True, text=True, timeout=60)
        return p.returncode, p.stdout, p.stderr


class Cli(unittest.TestCase):
    def test_balance_text_and_json(self):
        code, out, _ = run("{file}", "balance")
        self.assertEqual((code, out.strip()), (0, "Balance: 1873.43"))
        code, out, _ = run("{file}", "balance", "--json")
        self.assertEqual(json.loads(out), {"balance": "1873.43"})

    def test_as_of_applies_to_every_command(self):
        _, out, _ = run("{file}", "balance", "--json", "--as-of", "2026-01-31")
        self.assertEqual(json.loads(out), {"balance": "1984.51"})
        _, out, _ = run("{file}", "monthly", "--json", "--as-of", "2026-02-28")
        self.assertEqual([r["month"] for r in json.loads(out)], ["2026-01", "2026-02"])

    def test_categories_json(self):
        _, out, _ = run("{file}", "categories", "--json")
        self.assertEqual(list(json.loads(out).items()),
                         [("food", "-80.10"), ("fun", "-46.47"), ("salary", "2000.00")])

    def test_monthly_json(self):
        _, out, _ = run("{file}", "monthly", "--json")
        rows = json.loads(out)
        self.assertEqual(rows[0], {"month": "2026-01", "income": "2000.00", "expense": "15.49", "net": "1984.51"})
        self.assertEqual(len(rows), 3)

    def test_recurring_json(self):
        _, out, _ = run("{file}", "recurring", "--json")
        self.assertEqual(json.loads(out), [{"payee": "netflix.com", "amount": "-15.49", "interval": "monthly", "count": 3}])

    def test_parse_error_exit_2(self):
        code, out, err = run("{file}", "balance", text=CSV + "2026-04-01,X,oops,food\n")
        self.assertEqual(code, 2)
        self.assertEqual(out, "")
        self.assertTrue(err.strip().startswith("line 7: "), err)

    def test_lenient_skips_and_reports(self):
        code, out, err = run("{file}", "balance", "--lenient", text=CSV + "2026-04-01,X,oops,food\n")
        self.assertEqual((code, out.strip()), (0, "Balance: 1873.43"))
        self.assertTrue(err.strip().startswith("skipped line 7: "), err)

    def test_missing_file_and_bad_as_of_exit_1(self):
        code, out, err = run("/nonexistent/x.csv", "balance")
        self.assertEqual((code, out), (1, ""))
        self.assertTrue(err.startswith("error: "), err)
        code, out, err = run("{file}", "balance", "--as-of", "31/01/2026")
        self.assertEqual((code, out), (1, ""))
        self.assertTrue(err.startswith("error: "), err)
