#!/usr/bin/env bash
# ABOUTME: Records the local commands for the pinned restore closure review.
# ABOUTME: Uses disposable fixtures and avoids deployed services.
set -eu
cd /home/outsider/Projects/Hermes_agent/LifeOS_plugin
export LIFEOS_MEMORY_SOURCE=/home/outsider/.cache/lifeos-plugin-memory/source-gate-20261002-mount-release/lifeos/LifeOS/install
export LIFEOS_HERMES_SOURCE=/home/outsider/.cache/lifeos-plugin-memory/source-gate-20261002-mount-release/hermes
export LIFEOS_TASK_HOOK_PATH="$LIFEOS_MEMORY_SOURCE/hooks/TaskGovernance.hook.ts"
export PYTHONPATH=".:tests:$LIFEOS_HERMES_SOURCE"
export PYTHONDONTWRITEBYTECODE=1
review_python=/home/outsider/.cache/lifeos-plugin-memory/memory-plugin-test-env/bin/python
review_raw=docs/agents/2026-10-02-sol-restore-closure-review/raw
case "$1" in
 focused) "$review_python" -W error::ResourceWarning -m unittest test_update_transaction test_update_worker test_memory_admin_dashboard test_mount_transaction test_memory_children ;;
 recorder) "$review_python" -m unittest discover -s development/tests -p test_capture.py ;;
 restore) "$review_python" "$review_raw/probe_restore_closure.py" ;;
 callers) "$review_python" "$review_raw/probe_caller_closure.py" ;;
 admission) "$review_python" "$review_raw/probe_recovery_admission.py" ;;
 cleanup) "$review_python" "$review_raw/probe_cleanup.py" ;;
 recorder-probe) "$review_python" "$review_raw/probe_recorder.py" ;;
 *) exit 2 ;;
esac
