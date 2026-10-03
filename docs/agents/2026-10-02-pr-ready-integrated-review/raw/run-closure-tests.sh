#!/usr/bin/env bash
# ABOUTME: Runs isolated integrated review checks with pinned local source fixtures.
# ABOUTME: Saves raw verification output and an exit-status completion marker.
cd /home/outsider/Projects/Hermes_agent/LifeOS_plugin || exit 1
export LIFEOS_MEMORY_SOURCE=/home/outsider/.cache/lifeos-plugin-memory/source-gate-20261002-mount-release/lifeos/LifeOS/install
export LIFEOS_HERMES_SOURCE=/home/outsider/.cache/lifeos-plugin-memory/source-gate-20261002-mount-release/hermes
export LIFEOS_TASK_HOOK_PATH="$LIFEOS_MEMORY_SOURCE/hooks/TaskGovernance.hook.ts"
export PYTHONPATH=.:tests:$LIFEOS_HERMES_SOURCE
/home/outsider/.cache/lifeos-plugin-memory/memory-plugin-test-env/bin/python -W error::ResourceWarning -m unittest test_memory_admin_dashboard test_dashboard_api test_update_transaction -v > docs/agents/2026-10-02-pr-ready-integrated-review/raw/closure-tests.txt 2>&1
printf '%s\n' "$?" > docs/agents/2026-10-02-pr-ready-integrated-review/raw/closure-tests.done
node --test tests/test_dashboard_ui.cjs tests/test_memory_dashboard_ui.cjs > docs/agents/2026-10-02-pr-ready-integrated-review/raw/closure-ui-tests.txt 2>&1
printf '%s\n' "$?" > docs/agents/2026-10-02-pr-ready-integrated-review/raw/closure-ui-tests.done
