#!/usr/bin/env bash
# ABOUTME: Runs the prepared upgrade store and adjacent owner publication checks.
# ABOUTME: Retains complete test output and a completion status for detached execution.
set -u
cd /home/outsider/Projects/Hermes_agent/LifeOS_plugin || exit 1
export LIFEOS_MEMORY_SOURCE=/home/outsider/.cache/lifeos-daily-text-20261007/upgrade-store-final/lifeos/LifeOS/install
export LIFEOS_HERMES_SOURCE=/home/outsider/.cache/lifeos-daily-text-20261007/upgrade-store-final/hermes
export LIFEOS_HARVEST_CONTROL_SOURCE=/home/outsider/.cache/lifeos-daily-text-20261007/background-control-source/LifeOS/install
export LIFEOS_UPGRADE_CONTROL_SOURCE=/home/outsider/.cache/lifeos-daily-text-20261007/hypothesis-helpers-first/lifeos/LifeOS/install
export PYTHONPATH=/home/outsider/Projects/Hermes_agent/LifeOS_plugin:/home/outsider/Projects/Hermes_agent/LifeOS_plugin/tests
/home/outsider/.cache/lifeos-plugin-memory/memory-plugin-test-env/bin/python -W error -m unittest \
  test_memory_upgrade_store test_memory_proposal_delegation test_memory_proposals test_memory_hypothesis_helpers test_memory_hypothesis_review test_memory_hypothesis_relay test_memory_http \
  test_memory_pulse_relay test_memory_preferences test_memory_dashboard_response_authority \
  test_memory_publication_authority test_memory_publication_recovery test_memory_events \
  > docs/verification/2026-10-08-upgrade-store/adjacent-gate.txt 2>&1
result=$?
printf '%s\n' "$result" > docs/verification/2026-10-08-upgrade-store/adjacent-gate.done
exit "$result"
