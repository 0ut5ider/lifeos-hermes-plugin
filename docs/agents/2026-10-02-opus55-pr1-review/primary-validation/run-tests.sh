#!/usr/bin/env bash
# ABOUTME: Independently reruns the review test selection on the pinned sources.
# ABOUTME: Keeps primary verification output separate from the review evidence.
set -u
validation_output=/home/outsider/Projects/Hermes_agent/LifeOS_plugin/docs/agents/2026-10-02-opus55-pr1-review/primary-validation
cd /home/outsider/Projects/Hermes_agent/LifeOS_plugin || exit 1
export LIFEOS_MEMORY_SOURCE=/home/outsider/.cache/lifeos-plugin-memory/source-gate-20261002-mount-release/lifeos/LifeOS/install
export LIFEOS_HERMES_SOURCE=/home/outsider/.cache/lifeos-plugin-memory/source-gate-20261002-mount-release/hermes
export LIFEOS_TASK_HOOK_PATH="$LIFEOS_MEMORY_SOURCE/hooks/TaskGovernance.hook.ts"
export PYTHONPATH=".:tests:$LIFEOS_HERMES_SOURCE"
export LIFEOS_PREPARE_HERMES_REPO=/home/outsider/Projects/Hermes_agent/upstream/final-gate-baseline
export LIFEOS_PREPARE_LIFEOS_REPO=/home/outsider/.cache/lifeos-plugin-memory/managed-source
export PYTHONDONTWRITEBYTECODE=1
/home/outsider/.cache/lifeos-plugin-memory/memory-plugin-test-env/bin/python -W error::ResourceWarning -m unittest \
  test_mount_transaction test_memory_http test_memory_remount_relay \
  test_memory_administration test_memory_admin_install test_memory_admin_dashboard \
  test_lifeos_install_source test_dashboard_api test_update_worker test_update_transaction \
  test_memory_source_review test_memory_native test_memory_authorization test_memory_prompt \
  test_memory_sources test_memory_wiki_corpus test_memory_wiki_render test_memory_delegation \
  test_memory_runtime test_memory_preferences test_memory_dashboard test_memory_pulse_auth \
  test_hermes_memory_provider test_prepare_sources test_patch_bundle test_memory_restore \
  test_memory_mcp test_memory_sharing test_memory_service test_memory_policy test_memory_context \
  > "$validation_output/gate.txt" 2>&1
echo $? > "$validation_output/gate.exit"
/home/outsider/.cache/lifeos-plugin-memory/memory-plugin-test-env/bin/python -m unittest discover -s development/tests -p 'test_*.py' \
  > "$validation_output/development-tests.txt" 2>&1
echo $? > "$validation_output/development-tests.exit"
touch "$validation_output/.done"
