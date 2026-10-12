#!/bin/sh
# Remove the worktrees setup.sh made. Run the tally first: transcripts stay, worktrees go.
#   cleanup.sh DEST
set -eu
dest=${1:?usage: cleanup.sh DEST}
repo=$(sed -n 1p "$dest/.bench")
for wt in "$dest"/arm-*-*; do
  [ -d "$wt" ] || continue
  git -C "$repo" worktree remove --force "$wt" && echo "removed: $wt"
done
git -C "$repo" worktree prune
