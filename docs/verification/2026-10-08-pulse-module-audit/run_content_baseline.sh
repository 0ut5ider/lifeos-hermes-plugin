#!/usr/bin/env bash
# ABOUTME: Runs the prepared operational views and neighboring owner publication and relay checks.
# ABOUTME: Retains complete output and a completion status for detached execution.
set -u
cd /home/outsider/Projects/Hermes_agent/LifeOS_plugin || exit 1
export PATH=/home/outsider/.bun/bin:$PATH
export LIFEOS_MEMORY_SOURCE=/home/outsider/.cache/lifeos-daily-text-20261007/local-intelligence-first/lifeos/LifeOS/install
export LIFEOS_HERMES_SOURCE=/home/outsider/.cache/lifeos-daily-text-20261007/local-intelligence-first/hermes
export LIFEOS_PREPARE_HERMES_REPO=/home/outsider/.cache/lifeos-daily-text-20261007/channel-sources/hermes
export LIFEOS_PREPARE_LIFEOS_REPO=/home/outsider/.cache/lifeos-daily-text-20261007/channel-sources/lifeos
export LIFEOS_HARVEST_CONTROL_SOURCE=/home/outsider/.cache/lifeos-daily-text-20261007/background-control-source/LifeOS/install
export LIFEOS_FRESHNESS_CONTROL_SOURCE=/home/outsider/.cache/lifeos-daily-text-20261007/background-control-source/LifeOS/install
export LIFEOS_UPGRADE_CONTROL_SOURCE=/home/outsider/.cache/lifeos-daily-text-20261007/hypothesis-helpers-first/lifeos/LifeOS/install
export PYTHONPATH=/home/outsider/Projects/Hermes_agent/LifeOS_plugin:/home/outsider/Projects/Hermes_agent/LifeOS_plugin/tests
/home/outsider/.cache/lifeos-plugin-memory/memory-plugin-test-env/bin/python -W error -m unittest -v test_memory_content.MemoryContentTests.test_original_native_fold_order_delete_unset_and_torn_tail test_memory_content.MemoryContentTests.test_anonymous_board_status_and_stream_refuse_before_personal_reads test_memory_content.MemoryContentTests.test_owner_complete_board_and_status_match_actual_native_fold test_memory_content.MemoryContentTests.test_complete_history_exceeds_one_mib_without_losing_first_items test_memory_content.MemoryContentTests.test_excluded_later_event_refuses_whole_fold_instead_of_resurrecting_older_item test_memory_content.MemoryContentTests.test_current_authority_origin_bearer_and_connector_govern_delivery test_memory_content.MemoryContentTests.test_manual_actions_authenticate_then_refuse_until_governed_publication > docs/verification/2026-10-08-pulse-module-audit/content-baseline.txt 2>&1
result=$?
printf '%s\n' "$result" > docs/verification/2026-10-08-pulse-module-audit/content-baseline.done
exit "$result"
