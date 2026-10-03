#!/usr/bin/env bash
# ABOUTME: Runs isolated integrated review checks with pinned local source fixtures.
# ABOUTME: Saves raw verification output and an exit-status completion marker.
cd /home/outsider/Projects/Hermes_agent/LifeOS_plugin || exit 1
export LIFEOS_MEMORY_SOURCE=/home/outsider/.cache/lifeos-plugin-memory/source-gate-20261002-mount-release/lifeos/LifeOS/install
export LIFEOS_HERMES_SOURCE=/home/outsider/.cache/lifeos-plugin-memory/source-gate-20261002-mount-release/hermes
export LIFEOS_TASK_HOOK_PATH="$LIFEOS_MEMORY_SOURCE/hooks/TaskGovernance.hook.ts"
export PYTHONPATH=.:tests:$LIFEOS_HERMES_SOURCE
review_python=/home/outsider/.cache/lifeos-plugin-memory/memory-plugin-test-env/bin/python
"$review_python" -W error::ResourceWarning -m unittest test_memory_admin_dashboard test_memory_admin_install test_memory_administration test_mount_transaction test_update_transaction test_update_worker test_lifeos_install_source test_dashboard_api test_memory_preferences test_memory_runtime test_memory_policy test_memory_children test_memory_restore test_memory_prompt test_hermes_memory_provider test_hermes_patch_regeneration -v > docs/agents/2026-10-02-pr-ready-integrated-review/raw/python-tests.txt 2>&1
printf '%s\n' "$?" > docs/agents/2026-10-02-pr-ready-integrated-review/raw/python-tests.done
"$review_python" -m unittest discover -s development/tests -v > docs/agents/2026-10-02-pr-ready-integrated-review/raw/recorder-tests.txt 2>&1
printf '%s\n' "$?" > docs/agents/2026-10-02-pr-ready-integrated-review/raw/recorder-tests.done
node --test tests/test_dashboard_ui.cjs tests/test_memory_dashboard_ui.cjs > docs/agents/2026-10-02-pr-ready-integrated-review/raw/ui-tests.txt 2>&1
printf '%s\n' "$?" > docs/agents/2026-10-02-pr-ready-integrated-review/raw/ui-tests.done
