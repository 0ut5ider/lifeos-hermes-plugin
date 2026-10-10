#!/usr/bin/env bash
# ABOUTME: Runs the prepared operational views and neighboring owner publication and relay checks.
# ABOUTME: Retains complete output and a completion status for detached execution.
set -u
cd /home/outsider/Projects/Hermes_agent/LifeOS_plugin || exit 1
export PATH=/home/outsider/.bun/bin:$PATH
export LIFEOS_MEMORY_SOURCE=/home/outsider/.cache/lifeos-daily-text-20261007/menubar-second/lifeos/LifeOS/install
export LIFEOS_HERMES_SOURCE=/home/outsider/.cache/lifeos-daily-text-20261007/menubar-second/hermes
export LIFEOS_PREPARE_HERMES_REPO=/home/outsider/.cache/lifeos-daily-text-20261007/channel-sources/hermes
export LIFEOS_PREPARE_LIFEOS_REPO=/home/outsider/.cache/lifeos-daily-text-20261007/channel-sources/lifeos
export LIFEOS_HARVEST_CONTROL_SOURCE=/home/outsider/.cache/lifeos-daily-text-20261007/background-control-source/LifeOS/install
export LIFEOS_FRESHNESS_CONTROL_SOURCE=/home/outsider/.cache/lifeos-daily-text-20261007/background-control-source/LifeOS/install
export LIFEOS_UPGRADE_CONTROL_SOURCE=/home/outsider/.cache/lifeos-daily-text-20261007/hypothesis-helpers-first/lifeos/LifeOS/install
export PYTHONPATH=/home/outsider/Projects/Hermes_agent/LifeOS_plugin:/home/outsider/Projects/Hermes_agent/LifeOS_plugin/tests
/home/outsider/.cache/lifeos-plugin-memory/memory-plugin-test-env/bin/python -W error -m unittest -v test_memory_local_intelligence.MemoryLocalIntelligenceTests.test_original_primary_fallback_empty_and_status_characterization test_memory_local_intelligence.MemoryLocalIntelligenceTests.test_original_native_history_windows_order_dedupe_and_bad_range test_memory_local_intelligence.MemoryLocalIntelligenceTests.test_anonymous_reads_refuse_personal_digest_and_history test_memory_local_intelligence.MemoryLocalIntelligenceTests.test_owner_latest_and_complete_history_preserve_native_fields test_memory_local_intelligence.MemoryLocalIntelligenceTests.test_excluded_primary_cannot_fall_back_and_private_history_refuses test_memory_local_intelligence.MemoryLocalIntelligenceTests.test_current_authority_origin_bearer_and_connector_govern_delivery test_memory_local_intelligence.MemoryLocalIntelligenceTests.test_methods_selectors_and_refresh_refuse_before_job_execution > docs/verification/2026-10-08-pulse-module-audit/local-intelligence-read-baseline.txt 2>&1
result=$?
printf '%s\n' "$result" > docs/verification/2026-10-08-pulse-module-audit/local-intelligence-read-baseline.done
exit "$result"
