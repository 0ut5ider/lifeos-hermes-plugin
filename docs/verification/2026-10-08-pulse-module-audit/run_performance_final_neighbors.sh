#!/usr/bin/env bash
# ABOUTME: Runs the prepared operational views and neighboring owner publication and relay checks.
# ABOUTME: Retains complete output and a completion status for detached execution.
set -u
cd /home/outsider/Projects/Hermes_agent/LifeOS_plugin || exit 1
export PATH=/home/outsider/.bun/bin:$PATH
export LIFEOS_MEMORY_SOURCE=/home/outsider/.cache/lifeos-daily-text-20261007/performance-third/lifeos/LifeOS/install
export LIFEOS_HERMES_SOURCE=/home/outsider/.cache/lifeos-daily-text-20261007/performance-third/hermes
export LIFEOS_PREPARE_HERMES_REPO=/home/outsider/.cache/lifeos-daily-text-20261007/channel-sources/hermes
export LIFEOS_PREPARE_LIFEOS_REPO=/home/outsider/.cache/lifeos-daily-text-20261007/channel-sources/lifeos
export LIFEOS_HARVEST_CONTROL_SOURCE=/home/outsider/.cache/lifeos-daily-text-20261007/background-control-source/LifeOS/install
export LIFEOS_FRESHNESS_CONTROL_SOURCE=/home/outsider/.cache/lifeos-daily-text-20261007/background-control-source/LifeOS/install
export LIFEOS_UPGRADE_CONTROL_SOURCE=/home/outsider/.cache/lifeos-daily-text-20261007/hypothesis-helpers-first/lifeos/LifeOS/install
export PYTHONPATH=/home/outsider/Projects/Hermes_agent/LifeOS_plugin:/home/outsider/Projects/Hermes_agent/LifeOS_plugin/tests
/home/outsider/.cache/lifeos-plugin-memory/memory-plugin-test-env/bin/python -W error -m unittest -v \
  test_memory_performance test_memory_ledger test_memory_operational_history test_memory_capabilities \
  test_memory_operational_views test_memory_life_source_review test_memory_source_review test_memory_sources \
  test_native_frontend_types test_patch_bundle test_prepare_sources \
  > docs/verification/2026-10-08-pulse-module-audit/performance-final-neighbors.txt 2>&1
result=$?
printf '%s\n' "$result" > docs/verification/2026-10-08-pulse-module-audit/performance-final-neighbors.done
if [ "$result" -eq 0 ]; then bash docs/verification/2026-10-08-pulse-module-audit/run_performance_final_build.sh; fi
exit "$result"
