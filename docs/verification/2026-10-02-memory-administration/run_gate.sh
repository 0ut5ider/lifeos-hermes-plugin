#!/usr/bin/env bash
# ABOUTME: Runs authenticated mounting and neighboring memory and installation contracts.
# ABOUTME: Saves the bounded result and completion marker outside the interactive process.
set -u
cd /home/outsider/Projects/Hermes_agent/LifeOS_plugin || exit 1
export LIFEOS_MEMORY_SOURCE=/home/outsider/.cache/lifeos-plugin-memory/source-gate-20261001-prompt-publication-release/lifeos/LifeOS/install
export LIFEOS_HERMES_SOURCE=/home/outsider/.cache/lifeos-plugin-memory/source-gate-20261001-prompt-publication-release/hermes
export LIFEOS_TASK_HOOK_PATH="$LIFEOS_MEMORY_SOURCE/hooks/TaskGovernance.hook.ts"
export PYTHONPATH=".:tests:$LIFEOS_HERMES_SOURCE"
export LIFEOS_PREPARE_HERMES_REPO=/home/outsider/Projects/Hermes_agent/upstream/final-gate-baseline
export LIFEOS_PREPARE_LIFEOS_REPO=/home/outsider/.cache/lifeos-plugin-memory/managed-source
/home/outsider/.cache/lifeos-plugin-memory/memory-plugin-test-env/bin/python -m unittest \
  test_memory_administration test_memory_admin_install test_memory_admin_dashboard \
  test_lifeos_install_source test_dashboard_api test_update_worker test_update_transaction \
  test_memory_source_review test_memory_native test_memory_authorization test_memory_prompt \
  test_memory_sources test_memory_wiki_corpus test_memory_wiki_render test_memory_delegation \
  test_memory_runtime test_memory_preferences test_memory_dashboard test_memory_pulse_auth \
  test_hermes_memory_provider test_prepare_sources test_patch_bundle \
  > docs/verification/2026-10-02-memory-administration/gate.txt 2>&1
result=$?
printf '%s\n' "$result" > docs/verification/2026-10-02-memory-administration/gate.done
exit "$result"
