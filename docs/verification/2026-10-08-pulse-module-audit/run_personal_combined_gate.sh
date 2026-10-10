#!/usr/bin/env bash
# ABOUTME: Runs the prepared operational views and neighboring owner publication and relay checks.
# ABOUTME: Retains complete output and a completion status for detached execution.
set -u
cd /home/outsider/Projects/Hermes_agent/LifeOS_plugin || exit 1
export PATH=/home/outsider/.bun/bin:$PATH
export LIFEOS_MEMORY_SOURCE=/home/outsider/.cache/lifeos-daily-text-20261007/personal-modules-second/lifeos/LifeOS/install
export LIFEOS_HERMES_SOURCE=/home/outsider/.cache/lifeos-daily-text-20261007/personal-modules-second/hermes
export LIFEOS_PREPARE_HERMES_REPO=/home/outsider/.cache/lifeos-daily-text-20261007/channel-sources/hermes
export LIFEOS_PREPARE_LIFEOS_REPO=/home/outsider/.cache/lifeos-daily-text-20261007/channel-sources/lifeos
export LIFEOS_HARVEST_CONTROL_SOURCE=/home/outsider/.cache/lifeos-daily-text-20261007/background-control-source/LifeOS/install
export LIFEOS_FRESHNESS_CONTROL_SOURCE=/home/outsider/.cache/lifeos-daily-text-20261007/background-control-source/LifeOS/install
export LIFEOS_UPGRADE_CONTROL_SOURCE=/home/outsider/.cache/lifeos-daily-text-20261007/hypothesis-helpers-first/lifeos/LifeOS/install
export PYTHONPATH=/home/outsider/Projects/Hermes_agent/LifeOS_plugin:/home/outsider/Projects/Hermes_agent/LifeOS_plugin/tests
/home/outsider/.cache/lifeos-plugin-memory/memory-plugin-test-env/bin/python -W error -m unittest \
  test_memory_personal_modules test_memory_atlas test_memory_manual_state test_memory_onboarding test_memory_capabilities test_memory_novelty test_memory_operational_history test_memory_native test_memory_operational_views test_memory_async_relay test_memory_telos_overview test_native_frontend_types test_memory_telos_editor test_memory_user_index_publish test_memory_owner_jobs test_memory_session_harvest test_memory_publication_recovery test_memory_user_index test_memory_life_source_review test_memory_source_review test_memory_prompt test_memory_context test_memory_context_builder test_memory_derived_sync test_memory_state_evidence test_memory_life_business test_memory_life_work test_memory_life_finances test_memory_life_health test_memory_life_relay test_memory_tab_freshness \
  test_memory_http test_memory_preferences test_memory_dashboard_response_authority \
  test_memory_sources test_memory_morning_brief test_daily_pulse_profile \
  test_patch_bundle test_prepare_sources \
  > docs/verification/2026-10-08-pulse-module-audit/personal-combined-gate.txt 2>&1
result=$?
printf '%s\n' "$result" > docs/verification/2026-10-08-pulse-module-audit/personal-combined-gate.done
exit "$result"
