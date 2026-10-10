#!/usr/bin/env bash
# ABOUTME: Runs the prepared operational views and neighboring owner publication and relay checks.
# ABOUTME: Retains complete output and a completion status for detached execution.
set -u
cd /home/outsider/Projects/Hermes_agent/LifeOS_plugin || exit 1
export PATH=/home/outsider/.bun/bin:$PATH
export LIFEOS_MEMORY_SOURCE=/home/outsider/.cache/lifeos-daily-text-20261007/content-disposal-first/lifeos/LifeOS/install
export LIFEOS_HERMES_SOURCE=/home/outsider/.cache/lifeos-daily-text-20261007/content-disposal-first/hermes
export LIFEOS_PREPARE_HERMES_REPO=/home/outsider/.cache/lifeos-daily-text-20261007/channel-sources/hermes
export LIFEOS_PREPARE_LIFEOS_REPO=/home/outsider/.cache/lifeos-daily-text-20261007/channel-sources/lifeos
export LIFEOS_HARVEST_CONTROL_SOURCE=/home/outsider/.cache/lifeos-daily-text-20261007/background-control-source/LifeOS/install
export LIFEOS_FRESHNESS_CONTROL_SOURCE=/home/outsider/.cache/lifeos-daily-text-20261007/background-control-source/LifeOS/install
export LIFEOS_UPGRADE_CONTROL_SOURCE=/home/outsider/.cache/lifeos-daily-text-20261007/hypothesis-helpers-first/lifeos/LifeOS/install
export PYTHONPATH=/home/outsider/Projects/Hermes_agent/LifeOS_plugin:/home/outsider/Projects/Hermes_agent/LifeOS_plugin/tests
/home/outsider/.cache/lifeos-plugin-memory/memory-plugin-test-env/bin/python -W error -m unittest -v test_memory_publication_recovery.MemoryPublicationRecoveryTests.test_expected_deleted_publication_restores_original_and_absent_targets test_memory_publication_recovery.MemoryPublicationRecoveryTests.test_later_recreation_of_expected_deleted_file_blocks_all_recovery > docs/verification/2026-10-08-remaining-reader-audit/conduit-capture-deletion-second.txt 2>&1
result=$?
printf '%s\n' "$result" > docs/verification/2026-10-08-remaining-reader-audit/conduit-capture-deletion-second.done
exit "$result"
