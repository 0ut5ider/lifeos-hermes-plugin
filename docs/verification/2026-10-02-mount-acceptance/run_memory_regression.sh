#!/usr/bin/env bash
# ABOUTME: Runs every memory module against the distributed prepared native sources.
# ABOUTME: Preserves output and completion independently from the interactive session.
set -u
cd /home/outsider/Projects/Hermes_agent/LifeOS_plugin || exit 1
export LIFEOS_MEMORY_SOURCE=/home/outsider/.cache/lifeos-plugin-memory/source-gate-20261002-mount-release/lifeos/LifeOS/install
export LIFEOS_HERMES_SOURCE=/home/outsider/.cache/lifeos-plugin-memory/source-gate-20261002-mount-release/hermes
export LIFEOS_TASK_HOOK_PATH="$LIFEOS_MEMORY_SOURCE/hooks/TaskGovernance.hook.ts"
export PYTHONPATH=".:tests:$LIFEOS_HERMES_SOURCE"
/home/outsider/.cache/lifeos-plugin-memory/memory-plugin-test-env/bin/python -m unittest discover -v -s tests -p 'test_memory*.py' \
 > docs/verification/2026-10-02-mount-acceptance/memory-regression.txt 2>&1
result=$?
printf '%s\n' "$result" > docs/verification/2026-10-02-mount-acceptance/memory-regression.done
exit "$result"
