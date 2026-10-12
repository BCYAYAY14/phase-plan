#!/bin/sh
# Make a benchmark from a bundled task: a fresh git repo from its starter, then the worktrees.
#   setup-task.sh TASK [RUNS] [DEST] [ARMS]      e.g. setup-task.sh ledger 2
# DEST defaults to ~/phase-bench/<task>. The starter never sees the hidden tests or the reference.
set -eu
here=$(cd "$(dirname "$0")" && pwd)
task=${1:?usage: setup-task.sh TASK [RUNS] [DEST] [ARMS]}
runs=${2:-2}
dest=${3:-$HOME/phase-bench/$task}
arms=${4:-A B C D}
src="$here/tasks/$task/starter"
[ -d "$src" ] || { echo "no task: $task (have: $(ls "$here/tasks"))"; exit 64; }
[ ! -e "$dest/.repo" ] || { echo "exists: $dest (remove it with cleanup.sh first)"; exit 1; }
mkdir -p "$dest"
cp -R "$src" "$dest/.repo"
git -C "$dest/.repo" init -q
git -C "$dest/.repo" add -A
git -C "$dest/.repo" -c user.name=bench -c user.email=bench@localhost commit -q -m "starter: $task"
"$here/setup.sh" "$dest/.repo" HEAD "$runs" "$dest" "$arms"
echo "$task" >> "$dest/.bench"
echo "Task text for every arm: $(python3 -c 'import json,sys; print(json.load(open(sys.argv[1]))["task"])' "$here/tasks/$task/task.json")"
echo "Verify: $(python3 -c 'import json,sys; print(json.load(open(sys.argv[1]))["verify"])' "$here/tasks/$task/task.json")"
