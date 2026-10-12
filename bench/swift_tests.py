#!/usr/bin/env python3
"""Run a Swift package's tests one per process, so a crash (fatalError) fails only that test.

  swift_tests.py PACKAGE_DIR [--only FILE_OF_TEST_IDS] [--jobs N]

Prints JSON: {"areas": {class: {"passed", "ran"}}, "failures": [...], "results": {test id: bool}}.
A test id is Module.Class/testName, as `swift test list` prints it.
"""
import json
import os
import subprocess
import sys
from concurrent.futures import ThreadPoolExecutor

ENV = {**os.environ, "DEVELOPER_DIR": "/Applications/Xcode.app/Contents/Developer"}


def main():
    pkg = os.path.abspath(sys.argv[1])
    only = None
    jobs = 8
    args = sys.argv[2:]
    while args:
        a = args.pop(0)
        if a == "--only":
            only = set(open(args.pop(0)).read().split())
        elif a == "--jobs":
            jobs = int(args.pop(0))
    b = subprocess.run(["swift", "build", "--build-tests"], cwd=pkg, env=ENV, capture_output=True, text=True, timeout=1800)
    if b.returncode != 0:
        errors = [l for l in b.stdout.splitlines() + b.stderr.splitlines() if "error:" in l][:5]
        print(json.dumps({"areas": {}, "failures": [{"test": "build", "error": " | ".join(errors)[:600]}], "results": {}, "build_failed": True}))
        return
    listed = subprocess.run(["swift", "test", "list", "--skip-build"], cwd=pkg, env=ENV, capture_output=True, text=True, timeout=600)
    tests = [t.strip() for t in listed.stdout.splitlines() if "/" in t]
    if only is not None:
        tests = [t for t in tests if t in only]

    def one(t):
        p = subprocess.run(["swift", "test", "--skip-build", "--filter", "^" + t.replace(".", "\\.") + "$"],
                           cwd=pkg, env=ENV, capture_output=True, text=True, timeout=300)
        out = p.stdout + p.stderr
        ok = p.returncode == 0 and "Executed 1 test, with 0 failures" in out
        why = ""
        if not ok:
            lines = [l for l in out.splitlines() if "error:" in l or "Fatal error" in l or "failed" in l.lower()]
            why = (lines[0] if lines else out[-200:]).strip()[:300]
        return t, ok, why

    results, failures, areas = {}, [], {}
    with ThreadPoolExecutor(max_workers=jobs) as pool:
        for t, ok, why in pool.map(one, tests):
            results[t] = ok
            cls = t.split("/")[0].split(".")[-1]
            a = areas.setdefault(cls, {"passed": 0, "ran": 0})
            a["ran"] += 1
            a["passed"] += ok
            if not ok:
                failures.append({"test": t, "error": why})
    print(json.dumps({"areas": areas, "failures": failures, "results": results}))


if __name__ == "__main__":
    main()
