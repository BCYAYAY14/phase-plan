# Changelog

## 2.4.0 (2026-10-13)

- Long work whose phases have disjoint files runs those phases as parallel subagents by default, each at its own tier, then verifies in the session. Short work stays in one session.

## 2.3.0 (2026-10-13)

- Long work is always planned, even in one session: phase-by-phase work keeps each phase's reading scoped, so the context grows more slowly. Small work still skips the table.

## 2.2.0 (2026-10-13)

- Design and front-end work (UI, layout, visual polish, interaction, motion, UI copy, choosing between designs) routes to Large by default; Mid only when the skill judges it enough, such as building an exact mockup or a mechanical UI change, and says why.

## 2.1.0 (2026-10-13)

- Tiers recalibrated: every phase starts at Mid; Large only for code the repo flags as delicate, a phase a Mid attempt failed, hard bugs that resist debugging, or on request.
- A plan that needs a stronger model than the session sends only those phases up to a subagent; the rest stays in the session.
- Scratch files stay in `.phase-plan/scratch/`; the session id is no longer logged.

## 2.0.0 (2026-10-12)

- Works in any repo: falls back to `.phase-plan/PHASES.md`, locally ignored, when there is no instruction file, so the plan never ships with the work; finds work in plans, `TODO.md`, `ROADMAP.md`, open issues and TODO comments; finds the project's own verify command.
- Tiers (Small, Mid, Large, Top) mapped to the models you have; routes for dollars on pay per token, for the top model's limit on a subscription; drops effort where the host has none.
- Tables gain "Done when" and "Files"; parallel phases only on disjoint files, each in its own worktree.
- Rulings are rows of their own, before the phase they block.
- Finished rows are removed, never ticked; stale "Next" text outside the block is removed.
- A done claim is checked against the code before a row is dropped.
- Says when the work is too small to phase.
- Running a phase: a fixed brief, one retry a tier up, then stop; each phase is logged.
- Modes: dry run, and pinned (every phase on one model).
- A worked example, an MIT licence.
- Phases run in one session by default, on the lowest tier the plan needs; subagents only for work that will not fit, parallel work, or on request, orchestrated from a Mid-tier session.
- The plan without an instruction file lives in `.phase-plan/`, locally ignored, so it never ships with the work.

## 1.0.0

- First version: phases with a model and effort each, written into `CLAUDE.md` or `AGENTS.md`.
