"""Run the hidden tests against one copy of the code and print JSON per area.
   run_hidden.py CODE_DIR HIDDEN_DIR"""
import json
import os
import sys
import unittest

code, hidden = map(os.path.abspath, sys.argv[1:3])
sys.path.insert(0, code)
os.environ["LEDGER_CODE_DIR"] = code
os.chdir(code)
areas = {}
failures = []
failed = set()


class Collect(unittest.TextTestResult):
    def _area(self, test):
        parts = test.id().split(".")
        module = parts[-1] if parts[0] == "unittest" else parts[0]
        return module.replace("test_", "", 1)

    def addSuccess(self, test):
        super().addSuccess(test)
        areas.setdefault(self._area(test), [0, 0])[0] += 1
        areas[self._area(test)][1] += 1

    def _fail(self, test, err):
        areas.setdefault(self._area(test), [0, 0])[1] += 1
        failures.append({"test": test.id(), "error": self._exc_info_to_string(err, test).strip().splitlines()[-1][:300]})

    def addFailure(self, test, err):
        super().addFailure(test, err)
        self._fail(test, err)

    def addSubTest(self, test, subtest, err):
        super().addSubTest(test, subtest, err)
        if err is not None and test.id() not in failed:
            failed.add(test.id())
            self._fail(test, err)

    def addError(self, test, err):
        super().addError(test, err)
        self._fail(test, err)


suite = unittest.defaultTestLoader.discover(hidden, top_level_dir=hidden)
runner = unittest.TextTestRunner(stream=open(os.devnull, "w"), resultclass=Collect)
runner.run(suite)
print(json.dumps({"areas": {k: {"passed": v[0], "ran": v[1]} for k, v in areas.items()}, "failures": failures}))
