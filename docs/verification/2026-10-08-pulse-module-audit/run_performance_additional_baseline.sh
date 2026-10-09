#!/usr/bin/env bash
# ABOUTME: Runs the prepared operational views and neighboring owner publication and relay checks.
# ABOUTME: Retains complete output and a completion status for detached execution.
set -u
cd /home/outsider/Projects/Hermes_agent/LifeOS_plugin || exit 1
export PATH=/home/outsider/.bun/bin:$PATH
export LIFEOS_MEMORY_SOURCE=/home/outsider/.cache/lifeos-daily-text-20261007/ledger-first/lifeos/LifeOS/install
export LIFEOS_HERMES_SOURCE=/home/outsider/.cache/lifeos-daily-text-20261007/ledger-first/hermes
export LIFEOS_PREPARE_HERMES_REPO=/home/outsider/.cache/lifeos-daily-text-20261007/channel-sources/hermes
export LIFEOS_PREPARE_LIFEOS_REPO=/home/outsider/.cache/lifeos-daily-text-20261007/channel-sources/lifeos
export LIFEOS_HARVEST_CONTROL_SOURCE=/home/outsider/.cache/lifeos-daily-text-20261007/background-control-source/LifeOS/install
export LIFEOS_FRESHNESS_CONTROL_SOURCE=/home/outsider/.cache/lifeos-daily-text-20261007/background-control-source/LifeOS/install
export LIFEOS_UPGRADE_CONTROL_SOURCE=/home/outsider/.cache/lifeos-daily-text-20261007/hypothesis-helpers-first/lifeos/LifeOS/install
export PYTHONPATH=/home/outsider/Projects/Hermes_agent/LifeOS_plugin:/home/outsider/Projects/Hermes_agent/LifeOS_plugin/tests
/home/outsider/.cache/lifeos-plugin-memory/memory-plugin-test-env/bin/python -W error -m unittest -v test_memory_performance.MemoryPerformanceTests.test_day_window_boundaries_and_encoded_or_duplicate_selectors_refuse test_memory_performance.MemoryPerformanceTests.test_present_optional_quota_history_and_call_sites_preserve_native_fields test_memory_performance.MemoryPerformanceTests.test_decoded_private_optional_quota_records_do_not_contribute_counts test_memory_performance.MemoryPerformanceTests.test_redirected_and_invalid_utf8_log_refuses > docs/verification/2026-10-08-pulse-module-audit/performance-additional-baseline.txt 2>&1
result=$?
printf '%s\n' "$result" > docs/verification/2026-10-08-pulse-module-audit/performance-additional-baseline.done
exit "$result"
