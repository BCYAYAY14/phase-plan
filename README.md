# phase-plan

A Claude Code skill that turns "what's left" in a repo into an ordered table of phases, each with the cheapest model and effort level that won't risk quality. It agrees the table with you, writes it into the repo's instruction file (`CLAUDE.md` or `AGENTS.md`; otherwise `.phase-plan/PHASES.md`, kept out of git), runs the plan (in one session by default), and logs each phase.

Version 2.4.0 · [CHANGELOG](CHANGELOG.md) · MIT

## Install

```bash
git clone https://github.com/BCYAYAY14/phase-plan ~/.claude/skills/phase-plan
```

Update with `git -C ~/.claude/skills/phase-plan pull`.

## Use

| Say | It does |
| --- | --- |
| `/phase-plan`, "plan the phases", "what's left and which model" | Reads the plan, issues and TODOs, proposes phases in chat, writes them once you agree |
| "/phase-plan dry run" | Proposes in chat, writes nothing |
| "run the plan", "run phase 2" | Runs the phases in this session, on the lowest tier the plan needs (it tells you if a cheaper session would do); long work with phases on separate files runs those phases as parallel subagents; otherwise subagents only for work too big for one session, or when you ask. Logs each phase and removes its row |
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

## Models

Every phase starts at Mid, except design and front-end work, which starts at Large unless the skill judges Mid enough (an exact mockup to build, or a mechanical UI change) and says why. It also goes up a tier when the repo flags the code as delicate, a Mid attempt failed, or you ask. Rows are chosen by tier (Small, Mid, Large, Top) and mapped to what you have: in Claude Code today Haiku 5.5, Sonnet 5.5, Opus 5.5 and Fable 5.1 (Fable only when you ask). On another host the skill maps tiers by price band. It asks once whether you pay per token or by subscription: per token it optimises dollars; on a subscription it protects the top model's usage limit.
