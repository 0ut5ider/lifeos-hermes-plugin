#!/usr/bin/env bash
# ABOUTME: Runs isolated integrated review checks with pinned local source fixtures.
# ABOUTME: Saves raw verification output and an exit-status completion marker.
cd /home/outsider/Projects/Hermes_agent/LifeOS_plugin || exit 1
export LIFEOS_MEMORY_SOURCE=/home/outsider/.cache/lifeos-plugin-memory/source-gate-20261002-mount-release/lifeos/LifeOS/install
export LIFEOS_HERMES_SOURCE=/home/outsider/.cache/lifeos-plugin-memory/source-gate-20261002-mount-release/hermes
export LIFEOS_TASK_HOOK_PATH="$LIFEOS_MEMORY_SOURCE/hooks/TaskGovernance.hook.ts"
export PYTHONPATH=.:tests:$LIFEOS_HERMES_SOURCE
/home/outsider/.cache/lifeos-plugin-memory/memory-plugin-test-env/bin/python -m unittest test_bridge test_plugin_lifecycle test_stop_cap_policy test_patch_bundle test_footprint_contracts test_hermes_install_source test_prepare_sources test_update_plan test_update_hooks test_update_dependencies test_release_transaction test_claude_adapter test_claude_reference_adapter test_native_task_hook test_memory_authorization test_memory_remount_relay test_memory_http test_memory_source_review test_memory_dashboard -v > docs/agents/2026-10-02-pr-ready-integrated-review/raw/neighbor-tests.txt 2>&1
printf '%s\n' "$?" > docs/agents/2026-10-02-pr-ready-integrated-review/raw/neighbor-tests.done
