#!/usr/bin/env bash
# ABOUTME: Runs the complete plugin and recorder regression against pinned prepared sources.
# ABOUTME: Records each command result and preserves skipped fixture cases for review.
set -u
cd /home/outsider/Projects/Hermes_agent/LifeOS_plugin || exit 1
verification_output=$PWD/docs/verification/2026-10-02-pr-readiness
export LIFEOS_MEMORY_SOURCE=/home/outsider/.cache/lifeos-plugin-memory/source-gate-20261002-mount-release/lifeos/LifeOS/install
export LIFEOS_HERMES_SOURCE=/home/outsider/.cache/lifeos-plugin-memory/source-gate-20261002-mount-release/hermes
export LIFEOS_HERMES_REBUILD_SOURCE=$LIFEOS_HERMES_SOURCE
export LIFEOS_TASK_HOOK_PATH=$LIFEOS_MEMORY_SOURCE/hooks/TaskGovernance.hook.ts
export PYTHONPATH=.:tests:$LIFEOS_HERMES_SOURCE
export LIFEOS_PREPARE_HERMES_REPO=/home/outsider/Projects/Hermes_agent/upstream/final-gate-baseline
export LIFEOS_PREPARE_LIFEOS_REPO=/home/outsider/.cache/lifeos-plugin-memory/managed-source
export PYTHONDONTWRITEBYTECODE=1
verification_python=/home/outsider/.cache/lifeos-plugin-memory/memory-plugin-test-env/bin/python
"$verification_python" -W error::ResourceWarning -m unittest discover -v -s tests > "$verification_output/regression.txt" 2>&1
echo $? > "$verification_output/regression.exit"
"$verification_python" -W error::ResourceWarning -m unittest discover -v -s development/tests > "$verification_output/recorder.txt" 2>&1
echo $? > "$verification_output/recorder.exit"
node --test tests/test_dashboard_ui.cjs tests/test_memory_dashboard_ui.cjs > "$verification_output/dashboard.txt" 2>&1
echo $? > "$verification_output/dashboard.exit"
touch "$verification_output/.done"
