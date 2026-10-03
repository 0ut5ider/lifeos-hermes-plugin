#!/usr/bin/env bash
# ABOUTME: Runs the final integrated admission and program transaction correction checks.
# ABOUTME: Uses prepared native fixtures and stores results without touching deployed systems.
cd /home/outsider/Projects/Hermes_agent/LifeOS_plugin || exit 1
export LIFEOS_MEMORY_SOURCE=/home/outsider/.cache/lifeos-plugin-memory/source-gate-20261002-mount-release/lifeos/LifeOS/install
export LIFEOS_HERMES_SOURCE=/home/outsider/.cache/lifeos-plugin-memory/source-gate-20261002-mount-release/hermes
export LIFEOS_TASK_HOOK_PATH="$LIFEOS_MEMORY_SOURCE/hooks/TaskGovernance.hook.ts"
export LIFEOS_PREPARE_HERMES_REPO="$LIFEOS_HERMES_SOURCE"
export LIFEOS_PREPARE_LIFEOS_REPO=/home/outsider/.cache/lifeos-plugin-memory/source-gate-20261002-mount-release/lifeos
export PYTHONPATH=.:tests:$LIFEOS_HERMES_SOURCE
export TMPDIR=/home/outsider/.cache/lifeos-plugin-memory
/home/outsider/.cache/lifeos-plugin-memory/memory-plugin-test-env/bin/python -W error::ResourceWarning -m unittest test_installation_lock test_memory_admin_dashboard test_dashboard_api test_update_transaction test_update_worker test_hermes_install_source test_prepare_sources -v > docs/agents/2026-10-02-pr-ready-integrated-review/raw/final-closure-tests.txt 2>&1
printf '%s\n' "$?" > docs/agents/2026-10-02-pr-ready-integrated-review/raw/final-closure-tests.done
