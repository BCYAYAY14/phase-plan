#!/usr/bin/env python3
"""Integration rework per run: what was spent after the work was nominally done.

  rework.py DEST [--targets FILE ...] [--json]

For each DEST/arm-<X>-<n> worktree it reads the run's transcripts (session and
subagents) and finds T0: the first FULL test run (no filter) after every target
file has been edited at least once. Rework is everything after T0:
  edits     Edit/Write/MultiEdit tool calls, plus shell commands that write a target file
            (a heuristic: the command names the file and writes), and the distinct files
  usd       the API cost of every response after T0 (same prices as tally.py)
  cross     edits by an agent to a file that a different agent edited first
            (only possible when phases ran as subagents)
Target files come from the task's task.json ("target_files") unless given.
A run that never reaches T0 reports rework as "no T0" (the work never finished).
"""
import argparse
import json
import re
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent))
import tally  # noqa: E402

EDIT_TOOLS = {"Edit", "Write", "MultiEdit", "NotebookEdit"}
FULL_TEST = [re.compile(r"\bswift test\b(?!.*--filter)"), re.compile(r"unittest discover(?!.*\s-k\s)(?!.*\s-p\s)")]


def events(files):
    """Every assistant response once, in time order, with its agent, cost and tool calls."""
    prices = tally.load_prices(HERE.parent / "prices.json")
    seen, out = set(), []
    for f in files:
        agent = f.stem if "subagents" in f.parts else "main"
        for line in open(f):
            try:
                o = json.loads(line)
            except ValueError:
                continue
            if o.get("type") != "assistant":
                continue
            m = o.get("message") or {}
            key = m.get("id") or o.get("uuid")
            calls = [c for c in (m.get("content") or []) if isinstance(c, dict) and c.get("type") == "tool_use"]
            u = m.get("usage") or {}
            first = key not in seen
            seen.add(key)
            usd = 0.0
            if first and u and m.get("model") and not m["model"].startswith("<"):
                usd = cost_of(m["model"], u, prices)
            out.append({"t": o.get("timestamp", ""), "agent": agent, "usd": usd, "calls": calls})
    return sorted(out, key=lambda e: e["t"])


def cost_of(model, u, prices):
    p = prices["models"].get(model)
    if not p:
        return 0.0
    cc = u.get("cache_creation") or {}
    w1 = cc.get("ephemeral_1h_input_tokens", 0) or 0
    w5 = cc.get("ephemeral_5m_input_tokens")
    if w5 is None:
        w5 = (u.get("cache_creation_input_tokens", 0) or 0) - w1
    inp, cr, out = u.get("input_tokens", 0) or 0, u.get("cache_read_input_tokens", 0) or 0, u.get("output_tokens", 0) or 0
    lc = p.get("long_context")
    if lc and inp + w5 + w1 + cr > lc["threshold"]:
        p = {**p, **{k: lc[k] for k in ("input", "output", "cache_read")}}
    usd = (inp * p["input"] + w5 * p["input"] * prices["cache_write_5m_multiplier"]
           + w1 * p["input"] * prices["cache_write_1h_multiplier"] + cr * p["cache_read"] + out * p["output"]) / 1e6
    return usd * (prices["fast_multiplier"] if u.get("speed") == "fast" else 1)


WRITES = re.compile(r"open\([^)]*['\"]w|write_text|\.write\(|sed -i|perl -pi|>\s*\S|\btee\b|^\s*python3?\s+(-I\s+)?\S+\.py\s")
READ_ONLY = re.compile(r"^\s*(grep|cat|ls|head|tail|wc|sed -n|awk|find|git (status|diff|log))\b")


def bash_edits(cmd, targets):
    """Target files a shell command writes, by heuristic.

    A redirect (`> file`, `tee file`) writes exactly that file. Otherwise a
    segment that writes (a Python write, sed -i, perl -pi, a script run with
    the file as an argument) writes the targets it names."""
    clean = re.sub(r"\d?>&\d|\d?>\s*/dev/null", " ", cmd)
    names = {Path(t).name: t for t in targets}
    head = clean.split("\n", 1)[0]  # redirects live on the first line, never in a heredoc body
    redirected = re.findall(r"(?:(?<![-=])>>?|\btee\s+(?:-a\s+)?)\s*['\"]?([^\s'\"<>|;&]+)", head)
    if redirected:
        return {names[Path(r).name] for r in redirected if Path(r).name in names}
    out = set()
    segments = [clean] if "<<" in clean else re.split(r"&&|;|\|\|?", clean)
    for seg in segments:
        if READ_ONLY.match(seg) or not WRITES.search(seg):
            continue
        out |= {t for n, t in names.items() if n in seg}
    return out


def rel(path, wt):
    try:
        return str(Path(path).resolve().relative_to(Path(wt).resolve()))
    except ValueError:
        return path


def analyse(wt, targets):
    files = tally.find_by_cwd(wt)
    evs = events(files)
    total = sum(e["usd"] for e in evs)
    edited, first_editor, t0_index = set(), {}, None
    cross = 0
    for i, e in enumerate(evs):
        for c in e["calls"]:
            inp = c.get("input") or {}
            if c.get("name") in EDIT_TOOLS:
                path = rel(inp.get("file_path", ""), wt)
                hit = {path} if path in targets else set()
                # a patch script written with Write and run later edits the targets it names
                if path.endswith((".py", ".sh")):
                    body = inp.get("content", "") or inp.get("new_string", "")
                    hit |= {t for t in targets if Path(t).name in body}
                for h in hit:
                    edited.add(h)
                    owner = first_editor.setdefault(h, e["agent"])
                    if owner != e["agent"]:
                        cross += 1
            elif c.get("name") == "Bash":
                cmd = inp.get("command", "")
                for path in bash_edits(cmd, targets):
                    edited.add(path)
                    owner = first_editor.setdefault(path, e["agent"])
                    if owner != e["agent"]:
                        cross += 1
                if t0_index is None and edited >= targets and any(p.search(cmd) for p in FULL_TEST):
                    t0_index = i
    r = {"usd_total": round(total, 2), "cross_agent_edits": cross, "agents": len({e["agent"] for e in evs})}
    if t0_index is None:
        r.update(t0=None, rework_edits=None, rework_files=None, rework_usd=None, rework_share=None)
        return r
    after = evs[t0_index + 1:]
    edits = []
    for e in after:
        for c in e["calls"]:
            inp = c.get("input") or {}
            if c.get("name") in EDIT_TOOLS:
                edits.append((e["agent"], rel(inp.get("file_path", ""), wt)))
            elif c.get("name") == "Bash":
                edits += [(e["agent"], p) for p in bash_edits(inp.get("command", ""), targets)]
    rusd = sum(e["usd"] for e in after)
    r.update(t0=evs[t0_index]["t"], rework_edits=len(edits), rework_files=len({p for _, p in edits}),
             rework_usd=round(rusd, 2), rework_share=round(rusd / total, 3) if total else None)
    return r


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("dest")
    ap.add_argument("--targets", nargs="*")
    ap.add_argument("--json", action="store_true")
    a = ap.parse_args()
    dest = Path(a.dest).expanduser().resolve()
    targets = set(a.targets or [])
    if not targets:
        task = (dest / ".bench").read_text().splitlines()[2]
        targets = set(json.loads((HERE / "tasks" / task / "task.json").read_text()).get("target_files", []))
    if not targets:
        sys.exit("no target files: give --targets or set target_files in task.json")
    rows = {}
    for wt in sorted(dest.iterdir()):
        if re.fullmatch(r"arm-[A-Za-z0-9]+-\d+", wt.name) and wt.is_dir():
            rows[wt.name] = analyse(wt, targets)
    if a.json:
        print(json.dumps(rows, indent=2))
        return
    print(f"{'run':10} {'total $':>8} {'rework $':>9} {'share':>6} {'edits':>6} {'files':>6} {'cross':>6} {'agents':>7}")
    for k, r in rows.items():
        if r["t0"] is None:
            print(f"{k:10} {r['usd_total']:8.2f} {'no T0':>9}")
            continue
        print(f"{k:10} {r['usd_total']:8.2f} {r['rework_usd']:9.2f} {r['rework_share']:6.0%} {r['rework_edits']:6} {r['rework_files']:6} {r['cross_agent_edits']:6} {r['agents']:7}")


if __name__ == "__main__":
    main()
