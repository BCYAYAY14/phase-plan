# phase-plan

A Claude Code skill that turns "what's left" in a repo into an ordered table of phases, each with the cheapest model and effort level that won't risk quality. It agrees the table with you, writes it into the repo's instruction file (`CLAUDE.md` or `AGENTS.md`; otherwise `.phase-plan/PHASES.md`, kept out of git), runs the plan (separable phases of long work in parallel, everything else in one session), and logs each phase.

**On long, multi-part work, it roughly halved the cost and finished 2 to 3× faster in our tests, with the same hidden-test scores. On small tasks it stays out of the way.** ([results](https://github.com/BCYAYAY14/phase-plan-bench/blob/main/RESULTS.md))

Version 2.6.3 · [CHANGELOG](CHANGELOG.md) · MIT

## Install

```bash
npx skills add BCYAYAY14/phase-plan -g -a claude-code
```

That installs only the skill (one file) into `~/.claude/skills/phase-plan/`; `npx skills update` updates it. Leave out `-a claude-code` to pick other agents.

## Use

| Say | It does |
| --- | --- |
| `/phase-plan`, "plan the phases", "what's left and which model" | Reads the plan files and TODOs (open issues only if you ask), proposes phases in chat, writes them once you agree |
| "/phase-plan dry run" | Proposes in chat, writes nothing |
| "run the plan", "run phase 2" | Runs the phases in one session, on the tier most of the work needs (it tells you if a cheaper session would do), sending harder phases up a tier; long work with phases on separate files runs those phases as parallel subagents; otherwise subagents only for work too big for one session, or when you ask. Logs each phase and removes its row |
| "/phase-plan pinned to opus medium" | Every phase on one model |

It tells you when the work is too small to need a plan. For long work it always plans: working phase by phase keeps the context small, which is where it saves, and phases that touch separate files run as parallel subagents, which finishes several times sooner at no extra cost.

## Example

A small web app with a `TODO.md` listing a CSV export, a broken date filter, and a README refresh. The skill proposes:

| # | Phase | Done when | Files | Spec | Model · effort |
| --- | --- | --- | --- | --- | --- |
| R1 | Ruling: CSV dates as ISO or locale? | Ruling recorded in TODO.md | none | TODO.md "Export" | none |
| 1 | Find why the date filter drops today's rows | Failing test reproduces it | `src/filter.ts`, `test/filter.test.ts` | TODO.md "Filter bug" | Sonnet · high |
| 2 | CSV export (after R1) | `npm test -- export` passes | `src/export/`, `test/export.test.ts` | TODO.md "Export" | Sonnet · medium |
| 3 | README: export section | Section exists, commands run | `README.md` | TODO.md "Docs" | Sonnet · low |
| 4 | Verify | `npm test && npm run lint` pass | none | `package.json` scripts | Haiku · low |

Every phase is Sonnet or below, so the skill runs the whole plan in one Sonnet session. Phases 1 and 2 touch different files, so they could run in parallel (each in its own worktree) if you ask.

## Does it help?

Roughly half the cost and 2 to 3× faster on long, multi-part work, at the same hidden-test scores; on small tasks, about the same as no plan. Measured, not assumed: results, protocol and the kit to reproduce them are in [phase-plan-bench](https://github.com/BCYAYAY14/phase-plan-bench). On a long task in a real 8,000-line Swift codebase, graded by the codebase's own hidden tests:

| Setup | Cost | Time | vs the same model alone |
| --- | --- | --- | --- |
| Sonnet alone | $4.09 | ~17 min | baseline |
| Sonnet + skill, one session | $2.62 | ~15 min | 36% cheaper |
| **Sonnet + skill, parallel phases** | **$1.97** | **~6 min** | **52% cheaper, ~3x faster** |
| Opus alone | $5.45 | ~17 min | baseline |
| Opus + skill, parallel phases | $2.56 | ~7.5 min | 53% cheaper, ~2x faster |
| Opus + skill, parallel phases, all on Opus | $3.41 | ~7 min | 37% cheaper, ~2.5x faster |

Means of two runs per setup. Opus + skill planned on Opus and handed most phases to Sonnet subagents.

**Coupled task.** A frozen copy of the skill on a text engine it had never seen (about 17,000 lines of Swift, three modules that call each other, 117 hidden tests). Rework is the share of cost spent after the first full test run:

| Setup | Cost | Time | Hidden tests | Rework | vs Sonnet alone |
| --- | --- | --- | --- | --- | --- |
| Sonnet alone | $5.10 | ~18 min | 96 to 97% | 8 to 24% | baseline |
| Sonnet + skill, its own choice (one session) | $3.96 | ~17 min | 96 to 97% | 3 to 4% | 22% cheaper |
| **Sonnet + skill, parallel phases** | **$3.06** | **~13 min** | **97 to 99%** | **1%** | **40% cheaper** |

Left to choose, it did not split the coupled work, and its savings did not come back as fix-up work. On short tasks, including changes that thread a new parameter through many files, it keeps to one session without a plan. Two runs per setup: see the [full results](https://github.com/BCYAYAY14/phase-plan-bench/blob/main/RESULTS.md).

## Models

Every phase starts at Mid, except design and front-end work, which starts at Large unless the skill judges Mid enough (an exact mockup to build, or a mechanical UI change) and says why. It also goes up a tier when the repo flags the code as delicate, a Mid attempt failed, or you ask. Rows are chosen by tier (Small, Mid, Large, Top) and mapped to what you have: in Claude Code today Haiku 5.5, Sonnet 5.5, Opus 5.5 and Fable 5.1 (Fable only when you ask). On another host the skill maps tiers by price band. It asks once whether you pay per token or by subscription: per token it optimises dollars; on a subscription it protects the top model's usage limit.

## Benchmark kit

In its own repo, [phase-plan-bench](https://github.com/BCYAYAY14/phase-plan-bench): worktree setup, a headless runner, a hidden-test grader, a rework measure and a transcript cost tally. The skill's evals are there too.

## Safety

The skill treats everything it reads (plans, TODOs, issues, comments) as data describing work, never as instructions: text aimed at an agent is quoted to you, not acted on. Open issues are read only when you ask, since anyone can write one. It runs only read-only git commands and the project's own verify command found in its config files, and it never commits or pushes. The benchmark kit lives in a separate repo and is not part of the install.
