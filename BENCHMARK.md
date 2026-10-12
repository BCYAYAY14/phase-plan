# Benchmark: does phasing save anything?

The kit runs from a clone of this repo at `~/phase-plan` (`git clone https://github.com/BCYAYAY14/phase-plan ~/phase-plan`), with the skill itself installed as the README says.

The skill changes two things at once: it splits work into sessions (phasing) and it sends each phase to a cheaper model (routing). Measured together, a saving cannot be attributed. Three arms separate them:

| Arm | Setup | Isolates |
| --- | --- | --- |
| A | One session, one model and effort, no subagents | The baseline |
| B | `/phase-plan` pinned to A's model and effort, every phase run as a subagent | Phasing alone: B minus A |
| C | `/phase-plan` with its own routing, every phase run as a subagent | Routing alone: C minus B |
| D | C, but the orchestrating session runs on Sonnet | Orchestrator tier: D minus C |
| E | One Sonnet session, no subagents | The cheaper model alone: E minus A; phasing on Sonnet: D minus E |
| F | A Sonnet session running `/phase-plan`, then the plan as the skill says (one session, hard phases up a tier) | Whether planning pays: F minus E; whether the skill finds the hard part: F's hidden score on `recur` |
| G | F on Opus, staying on Opus | Whether planning pays on Opus: G minus A |
| P | Sonnet + skill, phases with disjoint files as parallel subagents | Parallel against one session: P minus F, and wall time |
| Q | P from an Opus session (subagents at the plan's tiers) | Orchestrator tier with parallel phases: Q minus P |
| R | Q with every phase pinned to Opus | Opus subagents against routed ones: R minus Q |
| S | Sonnet + skill, forced into one session with no subagents | One session against parallel on the same plan: S minus P |

Every arm's total includes the planning turns, the context each phase reloads, the phase reports and the log edits. They are all in the same session's transcripts, and `tally.py` reads the subagents' transcripts with it.

## Quick start: the bundled task

`bench/tasks/ledger` is a task with nothing to do with any of your projects: a small Python command-line tool (standard library only) that reads a bank CSV. The starter has a stub parser, a balance with two planted bugs, and a `TODO.md` of seven items (parsing, the bug, reports, recurring-payment detection, the command line, tests, the README). `SPEC.md` pins every public name, so acceptance tests the agents never see can grade them: 44 hidden tests in five areas, which the reference solution passes in full.

```bash
~/phase-plan/bench/setup-task.sh ledger 2
```

That makes `~/phase-bench/ledger/arm-{A,B,C}-{1,2}`. Run step 3 below with `<TASK>` = `Complete every item in TODO.md so the code matches SPEC.md. Work only inside this directory.` and `<VERIFY>` = `python3 -m unittest discover -s tests`. Then:

```bash
python3 ~/phase-plan/bench/grade.py ~/phase-bench/ledger --review
python3 ~/phase-plan/tally.py --compare ~/phase-bench/ledger
```

The hidden tests and the reference live in this skill's `bench/tasks/ledger/`, outside the worktrees. `grade.py` checks every run's transcripts for a path into that directory and marks it `leak`; `tally.py` drops a leaking run from the means.

## 1. Or pick a task with a known answer from your own history

Replay a change that is already committed: the run starts at its parent, and the real commit is the answer key. A good task:
- has a spec that existed **before** the commit (a plan section, an issue);
- is mid-sized: roughly 5 to 30 files; too small and phasing loses by construction, too large and runs get expensive;
- has a cheap, objective check (a test suite that runs in minutes);
- has at least two separable parts, so a phase split is possible at all.

## 2. Make the worktrees

```bash
~/phase-plan/bench/setup.sh <repo> <reference-commit>^ 2
```

This makes `~/phase-bench/<repo>-<base>/arm-{A,B,C}-{1,2}`, six detached worktrees at the same commit. Two runs per arm is the minimum; a single run is noise.

## 3. Run each arm in a fresh session

Open one new Claude Code session per directory (desktop app: New session, choose the folder; terminal: `cd` there and run `claude`). Set the session's model and effort to the baseline (for example Opus · medium) in **every** arm, A, B and C, so the planner and orchestrator cost the same everywhere. Paste the arm's prompt, with `<TASK>` replaced by the same task text each time.

**A**
```text
<TASK>
Do all of it yourself in this session. Do not use subagents. Finish by running <VERIFY>.
```

**B** (replace `opus medium` with A's model and effort)
```text
/phase-plan pinned to opus medium. Run the phases as subagents. The remaining work is:
<TASK>
Write the phases without asking, then run every phase in order, logging each one. The last phase runs <VERIFY>.
```

**C** (and **D**, started with `--model sonnet` instead)
```text
/phase-plan. Run the phases as subagents. The remaining work is:
<TASK>
Write the phases without asking, then run every phase in order, logging each one. The last phase runs <VERIFY>.
```

Rules that keep it fair:
- Same task text, same base commit, same session model in all six.
- Do not intervene mid-run. If a run asks a question, give the same one-line answer in every arm and note it.
- Do not reuse a session; a new one per directory.
- Run arms interleaved (A1, B1, C1, A2, B2, C2) so a model or price change mid-day hits all arms alike.

### Or let a script run them

`bench/run.sh DEST RUN` runs one arm headless with `claude -p`, the same prompt, model and effort every time, tools limited to file edits, subagents, skills, `python3` and read-only git. Runs can go in parallel; cost is unaffected.

```bash
for r in arm-A-1 arm-B-1 arm-C-1 arm-D-1; do ~/phase-plan/bench/run.sh ~/phase-bench/ledger-xl $r & done; wait
```

Each run's final message is in `DEST/.logs/<run>.out`. `bench/tasks/ledger-xl` is the larger task: 13 items, a 620-line reference, 87 hidden tests. The results also use `graph`, a task built from a private Swift app's graphing engine (its source is not published). Integration rework (cost and edits after the first full test run) comes from `bench/rework.py DEST`. `bench/tasks/recur` is the hard one: an RRULE expansion engine (a subset of RFC 5545), 52 hidden tests, 29 of them the RFC's own worked examples, so the answers do not rest on the reference.

## 4. Grade quality before counting cost

A cheaper run that is worse saved nothing. `bench/grade.py` grades every run from a temporary copy and writes `grades.json`:

| Signal | What it is | For a replayed commit |
| --- | --- | --- |
| verify | The run's own check passes | `--verify "<VERIFY>"` |
| hidden | Acceptance tests the run never saw, per area, against the reference's totals | `--hidden DIR` if you have tests that only use names the spec fixes |
| review | A blind review, the same model and prompt for every run: spec fidelity, correctness, code quality, tests, docs, 1 to 5, plus a defect list | `--reference-commit SHA` shows the reviewer the real commit as one valid answer |
| diff | Files and lines changed | always |
| leak | The run read the answers | always |

```bash
python3 ~/phase-plan/bench/grade.py ~/phase-bench/<name> --review [--reviewer-model opus]
```

The reviewer runs as `claude -p` from `<dest>/.review`, so its tokens never count toward an arm. If `claude -p` cannot run (it needs a signed-in terminal), each prompt is saved as `.review/<run>.prompt.md`: paste it into any session on the reviewer model, save the JSON reply as `.review/<run>.review.json`, and grade again.

How to read quality: hidden tests are the objective score; the review catches what tests cannot (structure, test quality, docs) and is noisier, so trust a gap of a point or more, not a tenth. An arm that is cheaper but loses hidden points did not save anything.

## 5. Tally

```bash
python3 ~/phase-plan/tally.py --compare ~/phase-bench/<repo>-<base>
```

It prints each run's tokens, dollars by model and quality (verify, hidden %, review), the mean per arm with its range, and B minus A, C minus B and C minus A for cost and C minus A for quality. `--json` gives the same for a spreadsheet. For one run in detail: `tally.py --cwd <worktree> --by session`.

Reading it:
- **Dollars are the headline, not tokens.** Cache reads dominate the token count and cost a twentieth of fresh input, so token totals mislead. Quote output tokens and dollars.
- **On a subscription** the dollars are API-equivalent, a proxy for how much of the usage limit a run takes. What runs out first is usually the top model's allowance, so also read the per-model split.
- **A difference smaller than an arm's own range is noise.** Run more pairs before concluding.
- If B costs more than A, phasing does not pay at this task size, and the skill's "should this be phased at all?" threshold should move up.

## 6. Clean up and publish

```bash
~/phase-plan/bench/cleanup.sh ~/phase-bench/<repo>-<base>
```

Transcripts stay in `~/.claude/projects`, so the tally can be rerun later. Put the result in the README's Results table: the task, its size, runs per arm, pass counts, mean dollars per arm and the three differences.
