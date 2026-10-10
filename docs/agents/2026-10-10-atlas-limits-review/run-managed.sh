#!/bin/bash
set -u
cd /home/outsider/Projects/Hermes_agent/LifeOS_plugin
out=docs/agents/2026-10-10-atlas-limits-review
export PYTHONDONTWRITEBYTECODE=1
export PYTHONPATH=/home/outsider/Projects/Hermes_agent/LifeOS_plugin:/home/outsider/Projects/Hermes_agent/LifeOS_plugin/tests:/home/outsider/.cache/lifeos-daily-text-20261007/daily-text-0.2.0-content-fixed/hermes
export LIFEOS_HERMES_SOURCE=/home/outsider/.cache/lifeos-daily-text-20261007/daily-text-0.2.0-content-fixed/hermes
export LIFEOS_MEMORY_SOURCE=/home/outsider/.cache/lifeos-atlas-20261010/native-sync-final/LifeOS/install
/home/outsider/.cache/lifeos-plugin-memory/memory-plugin-test-env/bin/python "$out/managed-measure.py" > "$out/managed.stdout" 2> "$out/managed.stderr"
result=$?
printf '%s\n' "$result" > "$out/managed.exit"
touch "$out/managed.supervisor.done"
exit "$result"
