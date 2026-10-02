#!/usr/bin/env bash
# ABOUTME: Records the exact local review test and probe commands.
# ABOUTME: Requires the pinned reviewed checkout and the listed prepared fixtures.
set -eu
cd /home/outsider/Projects/Hermes_agent/LifeOS_plugin
export LIFEOS_MEMORY_SOURCE=/home/outsider/.cache/lifeos-plugin-memory/source-gate-20261002-mount-release/lifeos/LifeOS/install
export LIFEOS_HERMES_SOURCE=/home/outsider/.cache/lifeos-plugin-memory/source-gate-20261002-mount-release/hermes
export LIFEOS_TASK_HOOK_PATH="$LIFEOS_MEMORY_SOURCE/hooks/TaskGovernance.hook.ts"
export PYTHONPATH=".:tests:$LIFEOS_HERMES_SOURCE"
export PYTHONDONTWRITEBYTECODE=1
review_python=/home/outsider/.cache/lifeos-plugin-memory/memory-plugin-test-env/bin/python
review_raw=docs/agents/2026-10-02-sol-review-fixes/raw
"$review_python" -W error::ResourceWarning -m unittest test_update_transaction test_mount_transaction test_memory_children test_memory_admin_dashboard test_update_worker
"$review_python" -m unittest discover -s development/tests -p test_capture.py
"$review_python" -W error::ResourceWarning -m unittest test_memory_runtime test_memory_history test_hermes_memory_provider
"$review_python" "$review_raw/probe_restore.py"
"$review_python" "$review_raw/probe_callers.py"
"$review_python" "$review_raw/probe_child.py"
"$review_python" "$review_raw/probe_cleanup.py"
"$review_python" "$review_raw/probe_recorder.py"
