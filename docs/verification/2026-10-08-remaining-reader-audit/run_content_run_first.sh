#!/usr/bin/env bash
# ABOUTME: Runs the prepared operational views and neighboring owner publication and relay checks.
# ABOUTME: Retains complete output and a completion status for detached execution.
set -u
cd /home/outsider/Projects/Hermes_agent/LifeOS_plugin || exit 1
export PATH=/home/outsider/.bun/bin:$PATH
export LIFEOS_MEMORY_SOURCE=/home/outsider/.cache/lifeos-daily-text-20261007/content-run-first/lifeos/LifeOS/install
export LIFEOS_HERMES_SOURCE=/home/outsider/.cache/lifeos-daily-text-20261007/content-run-first/hermes
export LIFEOS_PREPARE_HERMES_REPO=/home/outsider/.cache/lifeos-daily-text-20261007/channel-sources/hermes
export LIFEOS_PREPARE_LIFEOS_REPO=/home/outsider/.cache/lifeos-daily-text-20261007/channel-sources/lifeos
export LIFEOS_HARVEST_CONTROL_SOURCE=/home/outsider/.cache/lifeos-daily-text-20261007/background-control-source/LifeOS/install
export LIFEOS_FRESHNESS_CONTROL_SOURCE=/home/outsider/.cache/lifeos-daily-text-20261007/background-control-source/LifeOS/install
export LIFEOS_UPGRADE_CONTROL_SOURCE=/home/outsider/.cache/lifeos-daily-text-20261007/hypothesis-helpers-first/lifeos/LifeOS/install
export PYTHONPATH=/home/outsider/Projects/Hermes_agent/LifeOS_plugin:/home/outsider/Projects/Hermes_agent/LifeOS_plugin/tests
/home/outsider/.cache/lifeos-plugin-memory/memory-plugin-test-env/bin/python -W error -m unittest -v test_native_content_actions test_memory_content_actions.MemoryContentActionTests.test_owner_run_request_sets_native_flag_once_without_changing_existing_ledger_bytes test_memory_content_actions.MemoryContentActionTests.test_owner_missing_run_request_keeps_the_complete_ledger test_memory_content_actions.MemoryContentActionTests.test_source_change_after_actual_plan_keeps_later_ledger_bytes test_memory_content_actions.MemoryContentActionTests.test_owner_revocation_after_actual_plan_refuses_append test_memory_content_actions.MemoryContentActionTests.test_excluded_event_refuses_run_before_ledger_append test_memory_content_actions.MemoryContentActionTests.test_anonymous_actions_refuse_before_ledger_or_source_changes > docs/verification/2026-10-08-remaining-reader-audit/content-run-first.txt 2>&1
result=$?
printf '%s\n' "$result" > docs/verification/2026-10-08-remaining-reader-audit/content-run-first.done
exit "$result"
