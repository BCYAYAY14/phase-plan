#!/bin/sh
# Run one benchmark arm headless, the same way every time, so runs are comparable.
#   run.sh DEST RUN          e.g. run.sh ~/phase-bench/ledger-xl arm-C-1
# Arms: A one Opus session; B phased on Opus; C phased and routed, Opus orchestrator;
#       D phased and routed, Sonnet orchestrator; E one Sonnet session; F a Sonnet session running the skill's default; G the same on Opus; P Sonnet + skill with non-overlapping phases as parallel subagents; Q the same from Opus; R the same with every phase pinned to Opus; S Sonnet + skill forced into one session. Every session runs at effort medium.
# Tools are limited to file edits, subagents, skills and python3/git-read/ls in the worktree.
set -eu
# Run from a private copy, so editing this file during a run cannot break the run.
if [ -z "${RUN_SH_COPY:-}" ]; then
  copy=$(mktemp -t run.sh)
  cp "$0" "$copy"
  RUN_SH_COPY=1 RUN_SH_HERE="$(cd "$(dirname "$0")" && pwd)" exec sh "$copy" "$@"
fi
here=$RUN_SH_HERE
dest=$(cd "${1:?usage: run.sh DEST RUN}" && pwd)
run=${2:?usage: run.sh DEST RUN}
wt="$dest/$run"
task=$(sed -n 3p "$dest/.bench")
json="$here/tasks/$task/task.json"
text=$(python3 -c 'import json,sys; print(json.load(open(sys.argv[1]))["task"])' "$json")
verify=$(python3 -c 'import json,sys; print(json.load(open(sys.argv[1]))["verify"])' "$json")
arm=$(echo "$run" | sed -E 's/^arm-([A-Za-z0-9]+)-[0-9]+$/\1/')
model=opus
case "$arm" in
  A|E) prompt="$text
Do all of it yourself in this session. Do not use subagents. Finish by running $verify."
     [ "$arm" = E ] && model=sonnet ;;
  B) prompt="/phase-plan pinned to opus medium. Run the phases as subagents. The remaining work is:
$text
Write the phases without asking, then run every phase in order from this session (do not restart), logging each one. The last phase runs $verify." ;;
  C|D) prompt="/phase-plan. Run the phases as subagents. The remaining work is:
$text
Write the phases without asking, then run every phase in order from this session (do not restart), logging each one. The last phase runs $verify."
     [ "$arm" = D ] && model=sonnet ;;
  F) prompt="/phase-plan. The remaining work is:
$text
Write the phases without asking, then run the plan as the skill says. The last phase runs $verify."
     model=sonnet ;;
  G) prompt="/phase-plan. The remaining work is:
$text
Write the phases without asking, then run the plan as the skill says, but stay on this session's model: do not restart on another tier. The last phase runs $verify." ;;
  P) prompt="/phase-plan. The remaining work is:
$text
Write the phases without asking. Then run every phase whose Files do not overlap as subagents in parallel, all at once, in this directory (no worktrees: their files are disjoint), each with the model and effort the plan gives it. Then run the verify phase. The last phase runs $verify."
     model=sonnet ;;
  Q|R) pin=""
     [ "$arm" = R ] && pin=" pinned to opus medium"
     prompt="/phase-plan$pin. The remaining work is:
$text
Write the phases without asking. Then run every phase whose Files do not overlap as subagents in parallel, all at once, in this directory (no worktrees: their files are disjoint), each with the model and effort the plan gives it. Stay on this session's model: do not restart on another tier. Then run the verify phase. The last phase runs $verify." ;;
  S) prompt="/phase-plan. The remaining work is:
$text
Write the phases without asking, then run every phase yourself in this session, in order, with no subagents. The last phase runs $verify."
     model=sonnet ;;
  *) echo "unknown arm $arm"; exit 64 ;;
esac
mkdir -p "$dest/.logs"
cd "$wt"
export DEVELOPER_DIR=/Applications/Xcode.app/Contents/Developer
start=$(date +%s)
claude -p "$prompt" --model "$model" --effort medium --permission-mode acceptEdits \
  --allowedTools "Read" "Edit" "Write" "Glob" "Grep" "Agent" "Task" "Skill" "TodoWrite" \
  "Bash(python3:*)" "Bash(ls:*)" "Bash(cat:*)" "Bash(mkdir:*)" "Bash(git status:*)" "Bash(git diff:*)" \
  "Bash(git rev-parse:*)" "Bash(git log:*)" "Bash(printf:*)" "Bash(echo:*)" \
  "Bash(swift:*)" "Bash(DEVELOPER_DIR=/Applications/Xcode.app/Contents/Developer swift:*)" "Bash(xcrun:*)" \
  > "$dest/.logs/$run.out" 2>&1 || echo "exit $? (see $dest/.logs/$run.out)"
echo "$run done in $(( $(date +%s) - start ))s"
