#!/bin/sh
# Make one detached worktree per arm and run, all at the same base commit.
#   setup.sh REPO BASE [RUNS] [DEST] [ARMS]
# REPO   the repository to benchmark on
# BASE   the commit every run starts from (the parent of the reference commit)
# RUNS   runs per arm, default 2
# DEST   default ~/phase-bench/<repo name>-<base>; keep it outside /tmp (its realpath moves)
# ARMS   default "A B C"
# Creates DEST/arm-<arm>-<n>. Nothing is committed; remove with cleanup.sh.
set -eu
[ $# -ge 2 ] || { sed -n '2,10p' "$0"; exit 64; }
repo=$(cd "$1" && git rev-parse --show-toplevel)
base=$(git -C "$repo" rev-parse --short "$2")
runs=${3:-2}
dest=${4:-$HOME/phase-bench/$(basename "$repo")-$base}
arms=${5:-A B C}
mkdir -p "$dest"
for arm in $arms; do
  n=1
  while [ "$n" -le "$runs" ]; do
    wt="$dest/arm-$arm-$n"
    if [ -e "$wt" ]; then echo "exists, kept: $wt"; else
      git -C "$repo" worktree add --detach "$wt" "$base" >/dev/null
      echo "made: $wt"
    fi
    n=$((n + 1))
  done
done
printf '%s\n%s\n' "$repo" "$base" > "$dest/.bench"
# The skill keeps its plan in .phase-plan/; ignore it locally so it never counts as delivered work.
excl="$(git -C "$repo" rev-parse --git-common-dir)/info/exclude"
case "$excl" in /*) ;; *) excl="$repo/$excl" ;; esac
mkdir -p "$(dirname "$excl")"
grep -qx '.phase-plan/' "$excl" 2>/dev/null || echo '.phase-plan/' >> "$excl"
echo "Next: open a fresh Claude Code session in each directory and paste that arm's prompt (BENCHMARK.md)."
