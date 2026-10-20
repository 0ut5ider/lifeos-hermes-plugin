#!/bin/bash
# ABOUTME: Removes one key at a time from UNIT_COMMANDS in a scratch copy and runs TransitionTests.
# ABOUTME: Each mutant must fail; the product checkout is not changed.
set -u
SRC=/home/outsider/Projects/Hermes_agent/LifeOS_plugin
PY=/home/outsider/.cache/lifeos-daily-promotion-20261014/frozen-test-environment/bin/python
HERMES=/home/outsider/.cache/lifeos-release-0.7.3-20261016/archive-integration-wgrx453d/package/hermes
for key in NONE ExecCondition ExecStartPre ExecStart ExecStartPost ExecReload ExecStop ExecStopPost; do
  W=$(mktemp -d "$HOME/agent-scratch/tmp/mut4.XXXX")
  cp -r "$SRC/optional" "$SRC/tests" "$W/"
  sed -i "s/^UNIT_COMMANDS = (\(.*\))/UNIT_COMMANDS = tuple(k for k in (\1) if k != '$key')/" "$W/optional/lifeos_release_manager/inplace_preparation.py"
  out=$(cd "$W" && TMPDIR=$HOME/agent-scratch/tmp LIFEOS_HERMES_SOURCE=$HERMES PYTHONPATH=$W:$HERMES "$PY" -B -m unittest discover -s tests -p test_inplace_preparation.py -k TransitionTests 2>&1 | tail -1)
  echo "without $key: $out"
  rm -rf "$W"
done
