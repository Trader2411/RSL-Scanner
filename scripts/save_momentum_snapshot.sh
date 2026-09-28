#!/usr/bin/env bash
set -euo pipefail
# Only generated MomentumRadar output belongs to this data commit.
git config user.name 'github-actions[bot]'
git config user.email '41898282+github-actions[bot]@users.noreply.github.com'
git add docs/momentum-radar/data.json docs/momentum-radar/watch.json docs/momentum-radar/snapshot.json
git add docs/momentum-radar/history/ docs/momentum-radar/watch-history/
if git diff --cached --quiet; then
  echo 'No new MomentumRadar snapshot to save.'
  exit 0
fi
git commit -m 'Refresh verified MomentumRadar snapshot'
# The independent RSL publisher can move main between our fetch and push.
# Retry transient push failures or non-fast-forward races; never overwrite remote work.
for attempt in 1 2 3; do
  git fetch origin main
  if ! git rebase origin/main; then
    git rebase --abort
    echo 'Conflicting remote edit: snapshot not pushed.' >&2
    exit 1
  fi
  if git push origin HEAD:main; then exit 0; fi
  echo "Push failed; refresh remote state and retry ${attempt}/3." >&2
done
echo 'Snapshot could not be saved after three attempts.' >&2
exit 1
