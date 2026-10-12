import json
import os
import subprocess
import sys
import tempfile
import unittest

CODE = os.environ.get("RECUR_CODE_DIR", os.getcwd())


def run(*args, ics=None):
    with tempfile.TemporaryDirectory() as d:
        path = os.path.join(d, "e.ics")
        if ics is not None:
            with open(path, "w") as f:
                f.write(ics)
        args = [a.replace("{ics}", path) for a in args]
        p = subprocess.run([sys.executable, "-m", "recur", *args], cwd=CODE, capture_output=True, text=True, timeout=60)
        return p.returncode, p.stdout, p.stderr


class Cli(unittest.TestCase):
    def test_rule_text_output(self):
        code, out, _ = run("FREQ=MONTHLY;BYDAY=-1FR", "--start", "2026-01-01", "--limit", "3")
        self.assertEqual((code, out), (0, "2026-01-30\n2026-02-27\n2026-03-27\n"))

    def test_rule_json_and_end(self):
        code, out, _ = run("FREQ=WEEKLY;BYDAY=MO,FR", "--start", "2026-01-01", "--end", "2026-01-12", "--json")
        self.assertEqual((code, json.loads(out)), (0, ["2026-01-02", "2026-01-05", "2026-01-09", "2026-01-12"]))

    def test_ics(self):
        code, out, _ = run("--ics", "{ics}", "--end", "2026-02-28", "--json", ics="DTSTART;VALUE=DATE:20260115\nRRULE:FREQ=MONTHLY\n")
        self.assertEqual((code, json.loads(out)), (0, ["2026-01-15", "2026-02-15"]))

    def test_errors_exit_1(self):
        cases = [("FREQ=NOPE", "--start", "2026-01-01", "--limit", "2"), ("FREQ=DAILY", "--start", "2026-01-01"),
                 ("FREQ=DAILY;COUNT=2", "--start", "01/01/2026"), ("FREQ=DAILY;COUNT=2",), ("--ics", "/nonexistent.ics", "--end", "2026-01-01"),
                 ("--ics", "{ics}",)]
        for args in cases:
            with self.subTest(args=args):
                code, out, err = run(*args, ics="DTSTART:20260101\n")
                self.assertEqual((code, out), (1, ""))
                self.assertTrue(err.startswith("error: "), err)
