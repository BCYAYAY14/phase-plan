---
name: phase-plan
description: Split the remaining work into ordered phases, each with a recommended model and effort level, agree them with the owner, then write them into the repo's handoff file. Use when the user says "/phase-plan", "split the remaining into phases", "plan the phases", "what's left and which model", or asks to recommend models or effort levels for upcoming work.
---

# Phase plan

Turn "what is left" into an ordered table of phases. Each phase gets a model and an effort level chosen to spend as few tokens as possible without risking quality. Then write the table into the handoff.

## 1. Read before planning

- The handoff: `CLAUDE.md` at the repo root (else `AGENTS.md`, else ask). Read it in full, and follow its rules on brevity, punctuation and where unbuilt work lives.
- Every plan, runbook or ledger the handoff names as the home of unbuilt work. Read the unchecked items and the open sections, not the whole history.
- `git status`, briefly. Another session may have finished something since the handoff was last updated. If a phase is already done, drop it and say so.

## 2. Consult

Reply in chat first. Do not write the file yet.

- Give the phases as a table: `# | Phase | Spec (where its detail lives) | Model · effort | Why` (the Why column only in chat).
- Below the table, list what blocks or is stale before a phase can run (wrong version numbers, missing changelog items, gates). Then the order, marking which phases can run in parallel.
- Ask with AskUserQuestion only when an answer would change the phases, for example whether to include a deferrable item. Otherwise recommend and move on.
- If the user has already said "write it" or "put it in the handoff", go straight to step 3 after the table.

## 3. Write it into the handoff

- Put the phases inside one block delimited by `<!-- phases:start -->` and `<!-- phases:end -->`, in the handoff's "Next" section. Replace that block if it exists. If it does not, replace the existing "Next" list.
- The handoff's table drops the Why column: `# | Phase | Spec | Model · effort`. Each Spec cell is a pointer (a file plus a section), never a restatement of the spec.
- Under the table, add "Before phase N:" bullets for stale or blocking facts, and one "After <milestone>:" line for work that comes later.
- Do not commit. Report in one line: the file, the line, and the number of phases.

## Choosing a model and an effort level

| Work | Model · effort |
| --- | --- |
| Fixed commands that pass or fail (build, test, verify, lint) | Haiku · low; move up a model only on a failure |
| Mechanical edits, renames, a runbook followed step by step, writing from an exact list | Sonnet · low |
| A clear spec confined to a few files | Sonnet · medium |
| A clear spec over a wide surface (two platforms, many screens, a screen check) | Sonnet · high |
| Delicate code with a known cause (layout, concurrency, sync, migrations, anything the landmines warn about) | Opus · medium |
| Diagnosis with an unknown cause, design, judgment against a contract | Opus · high |
| Hard bugs that resist debugging, cross-cutting architecture | Opus · xhigh, or Fable only when the owner asks |
| Owner-only steps (accounts, secrets, payments, devices, rulings) | none |

## Saving tokens

- Run verification once, after the last edit, as its own cheap phase. Never once per phase.
- Phases that touch disjoint files run in parallel.
- Opus never writes prose from a list, and Haiku never decides anything.
- A phase that waits on an owner ruling is a phase of its own, placed before the build that needs the ruling.
- Split a phase when one part is mechanical and another needs judgment. Merge phases that share their context, so it is read only once.

## Running a phase later

When asked to run a phase from the table, delegate it with the Agent tool, passing `model` and `effort` exactly as the table says. Once the phase is done and verified, tick or remove its row in the handoff.
