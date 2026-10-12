# Results

Every number here is from `BENCHMARK.md`'s protocol: the same task in fresh worktrees, headless `claude -p` runs with the same prompt, model and effort (medium), planning and handoff tokens included, quality graded before cost. Dollars are API list prices (`prices.json`); on a subscription read them as a share of the usage limit. Two runs per arm unless noted. Measured 2026-10-12 and 13 with Claude Opus 5.5, Sonnet 5.5 and Haiku 5.5.

## The long task: a real codebase

`graph`: a private Swift app's graphing engine (about 8,000 lines). Its calculus, statistics, complex-number and geometry modules were stripped to declarations and doc comments (about 1,350 lines of maths to rebuild). Graded by 29 of the app's own tests that the runs never saw, each in its own process.

| Arm | Mean $ | Range | Wall time | Hidden tests |
| --- | --- | --- | --- | --- |
| **Sonnet + skill, separable phases as parallel subagents** | **1.97** | 1.47 to 2.47 | **5 to 7.5 min** | 29/29, 29/29 |
| Opus + skill, parallel subagents at the plan's tiers | 2.56 | 2.52 to 2.59 | 7 to 8 min | 29/29, 29/29 |
| Sonnet + skill, one session | 2.62 | 2.28 to 2.96 | 13 to 16 min | 29/29, 29/29 |
| One Sonnet session, no skill | 4.09 | 3.87 to 4.31 | 16 to 17.5 min | 29/29, 29/29 |
| One Opus session, no skill | 5.45 | 5.44 to 5.46 | about 17 min | 29/29, 29/29 |

- The skill's default on long work (plan, then separable phases as parallel subagents on Sonnet) was cheapest and fastest: about half the cost of a plain Sonnet session and a third of a plain Opus one, two to three times sooner, at full marks.
- Planning helps even without splitting: in one session it cut Sonnet's cost by about 36%. The runs that planned made fewer, smaller requests (about 100k to 140k tokens of context against about 190k): working phase by phase keeps each phase's reading scoped.
- Opus bought nothing on this task.

## An unseen task with tightly coupled modules

Run on a frozen copy of the skill (v2.5.2) after a reader asked whether the savings hold when phases depend on each other. `text`: a private app's text engine (about 17,000 lines of Swift, never used to tune the skill) with three modules that call each other stripped to declarations: inline style spans, the block source (which reads and writes the spans) and undo (which records both). Removing them broke 227 of 405 tests across 17 test classes; 117 are hidden. Rework is the cost after the first full test run once every target file was edited (`bench/rework.py`).

| Arm | Mean $ | Range | Wall time | Hidden tests | Rework share |
| --- | --- | --- | --- | --- | --- |
| Sonnet + skill, forced parallel subagents | 3.06 | 2.60 to 3.52 | 12.5 to 13 min | 97%, 99% | 1%, 1% |
| Sonnet + skill, its own choice | 3.96 | 3.70 to 4.21 | 16 to 18 min | 96%, 97% | 4%, 3% |
| Sonnet + skill, forced one session | 4.35 | 4.25 to 4.46 | 17 to 19 min | 99%, 98% | 20%, 3% |
| One Sonnet session, no skill | 5.10 | 4.41 to 5.80 | 17 to 20 min | 96%, 97% | 8%, 24% |

- Left to choose, the skill did not split coupled work: both runs planned one session because the modules depend on each other. It cost about 22% less than Sonnet alone at the same quality.
- Forced parallel was still cheapest and fastest with almost no rework, because every declaration and doc comment was kept: the coupling was in behaviour, not in a changing interface.
- Where an interface does change (a new parameter threaded through many files, mostly mechanical), a plan cost more than no plan. Since 2.6.0 the skill sizes work by its new logic rather than its file count, skips the plan for that kind of change, and never runs phases in parallel when they share an interface the work is changing.

## Short tasks: Python, written from a spec

| Task | One Sonnet session | Sonnet + skill | One Opus session | Phased across subagents (old 1.x behaviour) |
| --- | --- | --- | --- | --- |
| `ledger-xl` (13 items, 87 hidden tests) | 0.88 | 0.76 | 1.59 | 1.11 to 2.09 |
| `recur` (RRULE engine, 52 hidden tests, 29 of them RFC 5545's own examples) | 0.63 | 0.77 | 1.38 | |
| `ledger` (7 items, 44 hidden tests, one run per arm) | | | 0.74 | 1.15 to 1.56 |

- Every run of every arm passed every hidden test, so these compare cost only.
- On short work, splitting across subagents always cost more (each subagent starts cold and re-reads what it needs); planning in one session cost about the same as not planning. The skill keeps short work in one session.
- On `recur` the skill sent the engine to Opus, which added cost and nothing else: Sonnet got all 29 RFC examples right alone. That is why every phase now starts at Mid and goes up a tier on evidence (design and front-end work excepted).

## What the review column said

A blind reviewer (Opus, high effort, the same prompt for every run) scored each submission 1 to 5. Two reviews of the same code differ by about 0.4, which is as large as every difference between arms, so the review does not separate them. Opus-written code scored slightly higher on the short tasks (about 4.6 to 4.8 against 4.1 to 4.4) but not on `graph`.

## Caveats

- Two runs per arm (one on `ledger`): directions are clear where ranges do not overlap, and the exact dollar figures are not precise.
- One machine, one week, medium effort throughout. Effort levels are not measured yet, nor a task that Sonnet fails.
- Runs cut off by the usage limit were discarded and rerun in fresh worktrees; no partial run is in these tables.
