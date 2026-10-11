# phase-plan

A Claude Code skill. It splits the remaining work in a repo into ordered phases, recommends a model and effort level for each (cheapest that does not risk quality), agrees them with the owner, then writes the table into the repo's handoff file (`CLAUDE.md` or `AGENTS.md`). When a phase is run later, it is delegated to a subagent with that model and effort.

## Install

```bash
git clone https://github.com/BCYAYAY14/phase-plan ~/.claude/skills/phase-plan
```

Then say "/phase-plan" or "split the remaining work into phases" in Claude Code.
