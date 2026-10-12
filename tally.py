#!/usr/bin/env python3
"""Tally tokens and dollars from Claude Code transcripts.

Reads the JSONL transcripts Claude Code writes under ~/.claude/projects/,
including each session's subagent transcripts, counts every API response once
(deduplicated by message id) and prices it with prices.json.

  tally.py --session ID [--session ID ...]   sessions by id (plus their subagents)
  tally.py --cwd PATH                        every session started in PATH or below
  tally.py --compare DIR                     one row per DIR/arm-<X>-<n> worktree, then means per arm
  tally.py FILE_OR_DIR ...                   explicit transcript files or directories

Options: --by session (one block per transcript), --json, --prices FILE.
Standard library only.
"""
import argparse
import json
import os
import re
import sys
from collections import defaultdict
from pathlib import Path

HERE = Path(__file__).resolve().parent
PROJECTS = Path.home() / ".claude" / "projects"
FIELDS = ("requests", "input", "cache_write_5m", "cache_write_1h", "cache_read", "output")


def load_prices(path):
    with open(path) as f:
        return json.load(f)


def session_files(top):
    """A top-level session transcript plus its subagents' transcripts."""
    files = [top]
    sub = top.with_suffix("") / "subagents"
    if sub.is_dir():
        files += sorted(sub.glob("*.jsonl"))
    return files


def find_sessions(ids):
    out = []
    for sid in ids:
        hits = list(PROJECTS.glob(f"*/{sid}.jsonl"))
        if not hits:
            sys.exit(f"no transcript for session {sid} under {PROJECTS}")
        for h in hits:
            out += session_files(h)
    return out


def transcript_cwd(path, probe=60):
    try:
        with open(path) as f:
            for i, line in enumerate(f):
                if i >= probe:
                    break
                try:
                    cwd = json.loads(line).get("cwd")
                except ValueError:
                    continue
                if cwd:
                    return cwd
    except OSError:
        pass
    return None


def under(cwd, root):
    cwd, root = os.path.realpath(cwd), os.path.realpath(root)
    return cwd == root or cwd.startswith(root + os.sep)


def find_by_cwd(root):
    out = []
    for top in PROJECTS.glob("*/*.jsonl"):
        cwd = transcript_cwd(top)
        if cwd and under(cwd, root):
            out += session_files(top)
    return out


def expand_paths(paths):
    out = []
    for p in map(Path, paths):
        if p.is_dir():
            out += sorted(p.rglob("*.jsonl"))
        elif p.exists():
            out.append(p)
        else:
            sys.exit(f"not found: {p}")
    return out


def tally(files):
    """Returns {model: {field: n}} and {file: {model: {field: n}}}."""
    seen = set()
    total = defaultdict(lambda: dict.fromkeys(FIELDS, 0))
    per_file = {}
    speeds = defaultdict(lambda: defaultdict(int))
    long_ctx = defaultdict(lambda: dict.fromkeys(FIELDS, 0))
    for path in files:
        mine = defaultdict(lambda: dict.fromkeys(FIELDS, 0))
        with open(path) as f:
            for line in f:
                try:
                    o = json.loads(line)
                except ValueError:
                    continue
                if o.get("type") != "assistant":
                    continue
                m = o.get("message") or {}
                u = m.get("usage")
                model = m.get("model")
                if not u or not model or model.startswith("<"):
                    continue
                key = m.get("id") or o.get("requestId") or o.get("uuid")
                if key in seen:
                    continue
                seen.add(key)
                cc = u.get("cache_creation") or {}
                w1h = cc.get("ephemeral_1h_input_tokens", 0) or 0
                w5m = cc.get("ephemeral_5m_input_tokens")
                if w5m is None:
                    w5m = (u.get("cache_creation_input_tokens", 0) or 0) - w1h
                row = {
                    "requests": 1,
                    "input": u.get("input_tokens", 0) or 0,
                    "cache_write_5m": w5m or 0,
                    "cache_write_1h": w1h,
                    "cache_read": u.get("cache_read_input_tokens", 0) or 0,
                    "output": u.get("output_tokens", 0) or 0,
                }
                prompt = row["input"] + row["cache_write_5m"] + row["cache_write_1h"] + row["cache_read"]
                speed = u.get("speed") or "standard"
                bucket = f"{model}|{speed}|{prompt}"
                for k, v in row.items():
                    mine[model][k] += v
                    total[model][k] += v
                speeds[model][speed] += 1
                # Remember long prompts so a model with long-context rates is priced per request.
                long_ctx[bucket]["requests"] += 1
                for k, v in row.items():
                    if k != "requests":
                        long_ctx[bucket][k] += v
        per_file[str(path)] = dict(mine)
    return dict(total), per_file, long_ctx


def price_rows(long_ctx, prices):
    """Dollars per model, priced request by request (long context and fast mode)."""
    models = prices["models"]
    w5, w1, fast = prices["cache_write_5m_multiplier"], prices["cache_write_1h_multiplier"], prices["fast_multiplier"]
    cost = defaultdict(float)
    unknown = set()
    for bucket, row in long_ctx.items():
        model, speed, prompt = bucket.rsplit("|", 2)
        p = models.get(model)
        if p is None:
            unknown.add(model)
            continue
        lc = p.get("long_context")
        if lc and int(prompt) > lc["threshold"]:
            p = {**p, **{k: lc[k] for k in ("input", "output", "cache_read")}}
        d = (row["input"] * p["input"]
             + row["cache_write_5m"] * p["input"] * w5
             + row["cache_write_1h"] * p["input"] * w1
             + row["cache_read"] * p["cache_read"]
             + row["output"] * p["output"]) / 1e6
        cost[model] += d * (fast if speed == "fast" else 1)
    return dict(cost), unknown


def fmt(n):
    return f"{n:,}"


def print_table(title, total, cost):
    print(title)
    head = ("model",) + FIELDS + ("tokens", "USD")
    rows = []
    sums = dict.fromkeys(FIELDS, 0)
    usd = 0.0
    for model in sorted(total):
        r = total[model]
        toks = sum(r[k] for k in FIELDS if k != "requests")
        c = cost.get(model)
        rows.append((model,) + tuple(fmt(r[k]) for k in FIELDS) + (fmt(toks), f"{c:.2f}" if c is not None else "?"))
        for k in FIELDS:
            sums[k] += r[k]
        usd += c or 0
    toks = sum(sums[k] for k in FIELDS if k != "requests")
    rows.append(("TOTAL",) + tuple(fmt(sums[k]) for k in FIELDS) + (fmt(toks), f"{usd:.2f}"))
    widths = [max(len(str(x)) for x in col) for col in zip(head, *rows)]
    for r in (head,) + tuple(rows):
        print("  " + "  ".join(str(x).rjust(w) if i else str(x).ljust(w) for i, (x, w) in enumerate(zip(r, widths))))
    print()
    return toks, usd


def summary(total, cost):
    toks = sum(r[k] for r in total.values() for k in FIELDS if k != "requests")
    out = sum(r["output"] for r in total.values())
    return {"tokens": toks, "output": out, "usd": round(sum(cost.values()), 4)}


def compare(root, prices, as_json):
    arms = defaultdict(list)
    rows = []
    gpath = Path(root) / "grades.json"
    grades = json.loads(gpath.read_text())["runs"] if gpath.exists() else {}
    for d in sorted(Path(root).iterdir()):
        m = re.fullmatch(r"arm-([A-Za-z0-9]+)-(\d+)", d.name)
        if not m or not d.is_dir():
            continue
        files = find_by_cwd(d)
        total, _, lc = tally(files)
        cost, unknown = price_rows(lc, prices)
        s = summary(total, cost)
        s.update(arm=m.group(1), run=int(m.group(2)), sessions=sum(1 for f in files if "subagents" not in f.parts),
                 by_model={k: round(v, 4) for k, v in cost.items()}, unknown=sorted(unknown))
        g = grades.get(d.name, {})
        s.update(verify_ok=g.get("verify_ok"), hidden_pct=g.get("hidden_pct"),
                 review=(g.get("review") or {}).get("mean"), leak=g.get("leak", False))
        if s["leak"]:
            print(f"  {d.name} read the answers (grade.py leak); left out of the means", file=sys.stderr)
            rows.append(s)
            continue
        rows.append(s)
        arms[m.group(1)].append(s)
    if not rows:
        sys.exit(f"no arm-<X>-<n> directories in {root}")
    def avg(v, k):
        xs = [x[k] for x in v if x.get(k) is not None]
        return sum(xs) / len(xs) if xs else None

    means = {a: {"runs": len(v),
                 "tokens": avg(v, "tokens"),
                 "usd": avg(v, "usd"),
                 "usd_min": min(x["usd"] for x in v),
                 "usd_max": max(x["usd"] for x in v),
                 "hidden_pct": avg(v, "hidden_pct"),
                 "review": avg(v, "review"),
                 "verify_passed": sum(1 for x in v if x.get("verify_ok"))} for a, v in sorted(arms.items())}
    if as_json:
        print(json.dumps({"runs": rows, "means": means}, indent=2))
        return
    print("Runs")
    def q(r):
        if not grades:
            return ""
        v = {True: "verify pass", False: "verify FAIL"}.get(r.get("verify_ok"), "verify -")
        h = "-" if r.get("hidden_pct") is None else f"{r['hidden_pct']:.0f}%"
        rv = "-" if r.get("review") is None else f"{r['review']:.1f}/5"
        return f"; {v}, hidden {h}, review {rv}" + ("; LEAK, excluded" if r.get("leak") else "")

    for r in rows:
        models = ", ".join(f"{k} ${v:.2f}" for k, v in r["by_model"].items())
        print(f"  arm {r['arm']} run {r['run']}: {fmt(r['tokens'])} tokens, ${r['usd']:.2f} ({models}); {r['sessions']} session(s){q(r)}")
    print("\nMeans per arm")
    for a, m in means.items():
        qual = ""
        if grades:
            h = "-" if m["hidden_pct"] is None else f"{m['hidden_pct']:.0f}%"
            rv = "-" if m["review"] is None else f"{m['review']:.1f}/5"
            qual = f"; quality: hidden {h}, review {rv}, verify passed {m['verify_passed']}/{m['runs']}"
        print(f"  {a}: {fmt(int(m['tokens']))} tokens, ${m['usd']:.2f} (range ${m['usd_min']:.2f} to ${m['usd_max']:.2f}, {m['runs']} runs){qual}")
    if "A" in means and "B" in means:
        print(f"\n  Phasing, B minus A: ${means['B']['usd'] - means['A']['usd']:+.2f}, {int(means['B']['tokens'] - means['A']['tokens']):+,} tokens")
    if "B" in means and "C" in means:
        print(f"  Routing, C minus B: ${means['C']['usd'] - means['B']['usd']:+.2f}, {int(means['C']['tokens'] - means['B']['tokens']):+,} tokens")
    if "A" in means and "C" in means:
        print(f"  Whole skill, C minus A: ${means['C']['usd'] - means['A']['usd']:+.2f}, {int(means['C']['tokens'] - means['A']['tokens']):+,} tokens")
    if "A" in means and "E" in means:
        print(f"  One Sonnet session vs one Opus session, E minus A: ${means['E']['usd'] - means['A']['usd']:+.2f}, {int(means['E']['tokens'] - means['A']['tokens']):+,} tokens")
    if "D" in means and "E" in means:
        print(f"  Phasing on Sonnet, D minus E: ${means['D']['usd'] - means['E']['usd']:+.2f}, {int(means['D']['tokens'] - means['E']['tokens']):+,} tokens")
    if "C" in means and "D" in means:
        print(f"  Orchestrator on Sonnet, D minus C: ${means['D']['usd'] - means['C']['usd']:+.2f}, {int(means['D']['tokens'] - means['C']['tokens']):+,} tokens")
    if grades and "A" in means and means["A"]["hidden_pct"] is not None:
        for arm in [x for x in means if x != "A" and means[x]["hidden_pct"] is not None]:
            print(f"  Quality, {arm} minus A: hidden {means[arm]['hidden_pct'] - means['A']['hidden_pct']:+.1f} points")
    print("\nA difference smaller than an arm's own range is noise." + ("" if grades else " No grades.json: run bench/grade.py first, quality is not shown."))


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("paths", nargs="*")
    ap.add_argument("--session", action="append", default=[])
    ap.add_argument("--cwd")
    ap.add_argument("--compare")
    ap.add_argument("--by", choices=["session"])
    ap.add_argument("--json", action="store_true")
    ap.add_argument("--prices", default=str(HERE / "prices.json"))
    a = ap.parse_args()
    prices = load_prices(a.prices)

    if a.compare:
        return compare(a.compare, prices, a.json)

    files = expand_paths(a.paths) + find_sessions(a.session) + (find_by_cwd(a.cwd) if a.cwd else [])
    files = list(dict.fromkeys(files))
    if not files:
        ap.error("name transcripts, --session, --cwd or --compare")
    total, per_file, lc = tally(files)
    cost, unknown = price_rows(lc, prices)

    if a.json:
        print(json.dumps({"files": [str(f) for f in files], "by_model": total,
                          "usd_by_model": cost, "summary": summary(total, cost),
                          "unpriced_models": sorted(unknown)}, indent=2))
        return
    if a.by == "session":
        for f, t in per_file.items():
            if t:
                _, _, flc = tally([Path(f)])
                fcost, _ = price_rows(flc, prices)
                print_table(f, t, fcost)
    print_table(f"All ({len(files)} transcript(s))", total, cost)
    if unknown:
        print("No price for: " + ", ".join(sorted(unknown)) + ". Add them to prices.json.")
    print(f"Prices: {prices.get('_source', a.prices)}")


if __name__ == "__main__":
    main()
