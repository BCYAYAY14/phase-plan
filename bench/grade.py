#!/usr/bin/env python3
"""Grade every run in a benchmark directory for quality, before any cost is compared.

  grade.py DEST [--verify CMD] [--hidden DIR] [--reference-commit SHA]
                [--review] [--reviewer-model opus] [--reviewer-effort high] [--jobs 6]

For each DEST/arm-<X>-<n> worktree it records:
  verify    the run's own check (default for a bundled task: its test command), pass or fail
  hidden    acceptance tests the run never saw, scored per area against the reference's totals
  diff      files and lines changed since the base commit
  leak      whether the run's transcripts touched the lab's bench/tasks (answers live there)
  review    with --review: a blind review by a fixed model, 1 to 5 on five axes, plus defects

Writes DEST/grades.json, which tally.py --compare reads. The reviewer runs from DEST/.review,
so its tokens never count toward any arm. Runs each worktree's code from a temporary copy.
"""
import argparse
import hashlib
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent))
import tally  # noqa: E402

AXES = ("spec_fidelity", "correctness", "code_quality", "tests", "docs")
REVIEW_PROMPT = """You are reviewing one submission for a coding task. You do not know who or what wrote it. Judge it only against the specification.

Score each axis from 1 (poor) to 5 (excellent):
- spec_fidelity: does it do everything the specification and the task list ask, with the exact public names and behaviour?
- correctness: are there bugs, unhandled cases, or behaviour that would fail a careful acceptance test? 5 means you found none.
- code_quality: clear structure, no dead code, sensible names, idiomatic, no needless complexity.
- tests: do the submission's own tests cover the specified behaviour, including edge cases?
- docs: is the README usage section complete and accurate?

Reply with JSON only, no prose, in exactly this shape:
{"spec_fidelity": n, "correctness": n, "code_quality": n, "tests": n, "docs": n, "defects": [{"severity": "high|medium|low", "what": "one line"}]}

=== TASK LIST ===
{todo}

=== SPECIFICATION ===
{spec}
{reference}
=== SUBMISSION (diff from the starting code) ===
{diff}
"""


def sh(args, cwd=None, timeout=600):
    return subprocess.run(args, cwd=cwd, capture_output=True, text=True, timeout=timeout)


def read_bench(dest):
    lines = (dest / ".bench").read_text().splitlines()
    return {"repo": lines[0], "base": lines[1], "task": lines[2] if len(lines) > 2 else None}


def full_diff(wt, base):
    """Tracked changes since base plus untracked files, as one diff."""
    out = sh(["git", "-C", str(wt), "diff", base, "--", ".", ":(exclude).phase-plan"]).stdout
    untracked = sh(["git", "-C", str(wt), "ls-files", "--others", "--exclude-standard"]).stdout.split()
    for f in untracked:
        out += sh(["git", "-C", str(wt), "diff", "--no-index", "/dev/null", f]).stdout
    return out


def diff_size(diff):
    files = len(re.findall(r"^diff --git ", diff, flags=re.M))
    added = sum(1 for l in diff.splitlines() if l.startswith("+") and not l.startswith("+++"))
    removed = sum(1 for l in diff.splitlines() if l.startswith("-") and not l.startswith("---"))
    return {"files": files, "added": added, "removed": removed}


def copy_code(wt):
    tmp = Path(tempfile.mkdtemp(prefix="grade-"))
    dst = tmp / "code"
    shutil.copytree(wt, dst, ignore=shutil.ignore_patterns(".git", "__pycache__", ".venv", "node_modules"))
    return tmp, dst


def run_hidden(runner, code, hidden):
    p = sh([sys.executable, "-I", str(runner), str(code), str(hidden)], timeout=600)
    try:
        return json.loads(p.stdout.strip().splitlines()[-1])
    except (ValueError, IndexError):
        return {"areas": {}, "failures": [{"test": "runner", "error": (p.stderr or p.stdout)[-300:]}]}


def _run_swift(code, ids_file):
    p = sh([sys.executable, "-I", str(HERE / "swift_tests.py"), str(code), "--only", str(ids_file)], timeout=3600)
    try:
        return json.loads(p.stdout.strip().splitlines()[-1])
    except (ValueError, IndexError):
        return {"areas": {}, "failures": [{"test": "runner", "error": (p.stderr or p.stdout)[-300:]}], "build_failed": True}


def swift_hidden(task_dir, task, code):
    """Swift tasks: put the original test files over the run's and run only the hidden ids.

    If that does not build (one wrong signature stops the whole target), fall back to one
    hidden file at a time over the run's own tests, so a run is scored on what does compile."""
    dst = code / task["test_dir"]
    dst.mkdir(parents=True, exist_ok=True)
    own = {f.name: f.read_bytes() for f in dst.glob("*.swift")}
    hidden_files = sorted((task_dir / "hidden").glob("*.swift"))
    for f in hidden_files:
        shutil.copy(f, dst / f.name)
    ids_all = task_dir / "hidden_ids.txt"
    r = _run_swift(code, ids_all)
    if not r.get("build_failed"):
        return r
    wanted = set(ids_all.read_text().split())
    merged = {"areas": {}, "failures": [], "results": {}, "per_file": True}
    for f in hidden_files:
        classes = set(re.findall(r"class\s+(\w+)\s*:\s*XCTestCase", f.read_text()))
        ids = [t for t in wanted if t.split("/")[0].split(".")[-1] in classes]
        if not ids:
            continue
        for g in dst.glob("*.swift"):
            g.unlink()
        for name, data in own.items():
            (dst / name).write_bytes(data)
        shutil.copy(f, dst / f.name)
        tmp_ids = code / ".hidden_ids_one.txt"
        tmp_ids.write_text("\n".join(ids) + "\n")
        one = _run_swift(code, tmp_ids)
        if one.get("build_failed"):
            for t in ids:
                cls = t.split("/")[0].split(".")[-1]
                a = merged["areas"].setdefault(cls, {"passed": 0, "ran": 0})
                a["ran"] += 1
            merged["failures"].append({"test": f.name, "error": "does not compile against the run: " + one["failures"][0]["error"][:200]})
            continue
        for cls, a in one["areas"].items():
            m = merged["areas"].setdefault(cls, {"passed": 0, "ran": 0})
            m["passed"] += a["passed"]
            m["ran"] += a["ran"]
        merged["failures"] += one["failures"]
    return merged


EXTRA_MARKERS = []


def leaked(wt):
    markers = (str(HERE / "tasks"), "phase-plan/bench/tasks", *EXTRA_MARKERS)
    for f in tally.find_by_cwd(wt):
        try:
            text = f.read_text(errors="ignore")
        except OSError:
            continue
        if any(m in text for m in markers):
            return True
    return False


def review(dest, key, prompt, model, effort):
    rdir = dest / ".review"
    rdir.mkdir(exist_ok=True)
    # Kept so a review can be pasted into any session when claude -p is unavailable; the reply
    # goes in <key>.review.json beside it. A saved review is reused while the prompt (the run's
    # diff) is unchanged; one pasted by hand has no hash and is always reused.
    (rdir / f"{key}.prompt.md").write_text(prompt)
    sha = hashlib.sha256(prompt.encode()).hexdigest()[:16]
    saved = rdir / f"{key}.review.json"
    if saved.exists():
        r = json.loads(saved.read_text())
        if r.get("_prompt_sha") in (None, sha):
            scores = [r.get(a) for a in AXES if isinstance(r.get(a), (int, float))]
            r["mean"] = round(sum(scores) / len(scores), 2) if scores else None
            return r
    args = ["claude", "-p", "--model", model, "--tools", "", "--no-session-persistence"]
    if effort:
        args += ["--effort", effort]
    p = subprocess.run(args, input=prompt, cwd=rdir, capture_output=True, text=True, timeout=1800)
    m = re.search(r"\{.*\}", p.stdout, flags=re.S)
    if not m:
        return {"error": (p.stderr or p.stdout)[-400:]}
    try:
        r = json.loads(m.group(0))
    except ValueError:
        return {"error": "reviewer reply was not JSON: " + p.stdout[-300:]}
    r["_prompt_sha"] = sha
    saved.write_text(json.dumps(r, indent=2))
    scores = [r.get(a) for a in AXES if isinstance(r.get(a), (int, float))]
    r["mean"] = round(sum(scores) / len(scores), 2) if scores else None
    return r


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("dest")
    ap.add_argument("--verify", help="shell command run in a copy of each worktree; exit 0 is a pass")
    ap.add_argument("--hidden", help="directory of hidden unittest files (a bundled task sets this)")
    ap.add_argument("--reference-commit", help="replay benchmarks: a known-good commit shown to the reviewer")
    ap.add_argument("--review", action="store_true", help="also run a blind review with claude -p")
    ap.add_argument("--reviewer-model", default="opus")
    ap.add_argument("--reviewer-effort", default="high")
    ap.add_argument("--jobs", type=int, default=6, help="reviews run at once (default 6)")
    a = ap.parse_args()

    dest = Path(a.dest).expanduser().resolve()
    bench = read_bench(dest)
    task_dir = HERE / "tasks" / bench["task"] if bench["task"] else None
    task = json.loads((task_dir / "task.json").read_text()) if task_dir else {}
    verify = a.verify or task.get("verify")
    hidden = Path(a.hidden) if a.hidden else (task_dir / "hidden" if task_dir else None)
    runner = task_dir / "run_hidden.py" if task_dir else HERE / "tasks" / "ledger" / "run_hidden.py"

    totals = None
    EXTRA_MARKERS.extend(task.get("leak_markers", []))
    if task.get("kind") == "swift":
        tmp, ref_code = copy_code(task_dir / "reference")
        try:
            ref = swift_hidden(task_dir, task, ref_code)
        finally:
            shutil.rmtree(tmp, ignore_errors=True)
        totals = {k: v["ran"] for k, v in ref["areas"].items()}
        if not totals or any(v["passed"] != v["ran"] for v in ref["areas"].values()):
            sys.exit("the reference fails its own hidden tests: " + json.dumps(ref.get("failures", [])[:3]))
        hidden = None
    if hidden and task_dir and (task_dir / "reference").is_dir():
        ref = run_hidden(runner, task_dir / "reference", hidden)
        totals = {k: v["ran"] for k, v in ref["areas"].items()}
        if any(v["passed"] != v["ran"] for v in ref["areas"].values()):
            sys.exit("the reference fails its own hidden tests; fix the task first")

    base = bench["base"]
    repo = bench["repo"]
    spec = sh(["git", "-C", repo, "show", f"{base}:SPEC.md"]).stdout or "(no SPEC.md at the base commit)"
    todo = sh(["git", "-C", repo, "show", f"{base}:TODO.md"]).stdout or "(no TODO.md at the base commit)"
    reference = ""
    if a.reference_commit:
        reference = ("\n=== A KNOWN-GOOD IMPLEMENTATION (one valid answer, not the only one) ===\n"
                     + sh(["git", "-C", repo, "show", a.reference_commit]).stdout)

    grades = {"totals": totals, "verify": verify, "runs": {}}
    old = {}
    if (dest / "grades.json").exists():
        old = json.loads((dest / "grades.json").read_text()).get("runs", {})
    prompts = {}
    for wt in sorted(dest.iterdir()):
        m = re.fullmatch(r"arm-([A-Za-z0-9]+)-(\d+)", wt.name)
        if not m or not wt.is_dir():
            continue
        key = wt.name
        g = {"arm": m.group(1), "run": int(m.group(2))}
        diff = full_diff(wt, base)
        g["diff"] = diff_size(diff)
        tmp, code = copy_code(wt)
        try:
            if verify:
                p = subprocess.run(verify, shell=True, cwd=code, capture_output=True, text=True, timeout=1800)
                g["verify_ok"] = p.returncode == 0
            if totals and (hidden or task.get("kind") == "swift"):
                h = swift_hidden(task_dir, task, code) if task.get("kind") == "swift" else run_hidden(runner, code, hidden)
                per = {area: min(h["areas"].get(area, {}).get("passed", 0), n) for area, n in totals.items()}
                g["hidden"] = per
                g["hidden_pct"] = round(100 * sum(per.values()) / sum(totals.values()), 1)
                g["hidden_failures"] = h["failures"][:20]
        finally:
            shutil.rmtree(tmp, ignore_errors=True)
        g["leak"] = leaked(wt)
        if a.review:
            prompts[key] = REVIEW_PROMPT.replace("{todo}", todo).replace("{spec}", spec) \
                                        .replace("{reference}", reference).replace("{diff}", diff or "(no changes)")
        elif "review" in old.get(key, {}):
            g["review"] = old[key]["review"]
        grades["runs"][key] = g
        print(f"graded {key}", file=sys.stderr)

    if prompts:
        print(f"reviewing {len(prompts)} run(s), {min(a.jobs, len(prompts))} at a time", file=sys.stderr)
        with ThreadPoolExecutor(max_workers=max(1, a.jobs)) as pool:
            futures = {k: pool.submit(review, dest, k, p, a.reviewer_model, a.reviewer_effort) for k, p in prompts.items()}
            for k, f in futures.items():
                grades["runs"][k]["review"] = f.result()

    (dest / "grades.json").write_text(json.dumps(grades, indent=2))
    areas = list(totals) if totals else []
    head = ["run", "verify", "hidden %"] + areas + ["review", "files", "+lines", "leak"]
    rows = []
    for key, g in grades["runs"].items():
        rv = g.get("review", {})
        verdict = {True: "pass", False: "FAIL"}.get(g.get("verify_ok"), "-")
        per = [f"{g['hidden'][x]}/{totals[x]}" for x in areas] if "hidden" in g else ["-"] * len(areas)
        score = "error" if "error" in rv else str(rv.get("mean", "-"))
        rows.append([key, verdict, str(g.get("hidden_pct", "-"))] + per
                    + [score, str(g["diff"]["files"]), str(g["diff"]["added"]), "YES" if g["leak"] else "no"])
    widths = [max(len(r[i]) for r in [head] + rows) for i in range(len(head))]
    for r in [head] + rows:
        print("  ".join(c.ljust(w) for c, w in zip(r, widths)))
    print(f"\nWrote {dest / 'grades.json'}. A run with leak YES read the answers; drop it.")


if __name__ == "__main__":
    main()
