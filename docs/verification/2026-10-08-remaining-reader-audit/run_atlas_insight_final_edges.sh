#!/usr/bin/env bash
# ABOUTME: Runs the prepared operational views and neighboring owner publication and relay checks.
# ABOUTME: Retains complete output and a completion status for detached execution.
set -u
cd /home/outsider/Projects/Hermes_agent/LifeOS_plugin || exit 1
export PATH=/home/outsider/.bun/bin:$PATH
export LIFEOS_MEMORY_SOURCE=/home/outsider/.cache/lifeos-daily-text-20261007/atlas-insight-fourth/lifeos/LifeOS/install
export LIFEOS_HERMES_SOURCE=/home/outsider/.cache/lifeos-daily-text-20261007/atlas-insight-fourth/hermes
export LIFEOS_PREPARE_HERMES_REPO=/home/outsider/.cache/lifeos-daily-text-20261007/channel-sources/hermes
export LIFEOS_PREPARE_LIFEOS_REPO=/home/outsider/.cache/lifeos-daily-text-20261007/channel-sources/lifeos
export LIFEOS_HARVEST_CONTROL_SOURCE=/home/outsider/.cache/lifeos-daily-text-20261007/background-control-source/LifeOS/install
export LIFEOS_FRESHNESS_CONTROL_SOURCE=/home/outsider/.cache/lifeos-daily-text-20261007/background-control-source/LifeOS/install
export LIFEOS_UPGRADE_CONTROL_SOURCE=/home/outsider/.cache/lifeos-daily-text-20261007/hypothesis-helpers-first/lifeos/LifeOS/install
export PYTHONPATH=/home/outsider/Projects/Hermes_agent/LifeOS_plugin:/home/outsider/Projects/Hermes_agent/LifeOS_plugin/tests
/home/outsider/.cache/lifeos-plugin-memory/memory-plugin-test-env/bin/python -W error -m unittest -v test_memory_atlas_insight_edges test_memory_atlas_jobs.MemoryAtlasJobAuthenticationTests > docs/verification/2026-10-08-remaining-reader-audit/atlas-insight-final-edges.txt 2>&1
result=$?
printf '%s\n' "$result" > docs/verification/2026-10-08-remaining-reader-audit/atlas-insight-final-edges.done
exit "$result"
