#!/usr/bin/env bash
# ABOUTME: Runs the prepared morning brief and adjacent owner job checks.
# ABOUTME: Retains complete test output and a completion status for detached execution.
set -u
cd /home/outsider/Projects/Hermes_agent/LifeOS_plugin || exit 1
export LIFEOS_MEMORY_SOURCE=/home/outsider/.cache/lifeos-daily-text-20261007/morning-brief-final/lifeos/LifeOS/install
export LIFEOS_HERMES_SOURCE=/home/outsider/.cache/lifeos-daily-text-20261007/morning-brief-final/hermes
export LIFEOS_HARVEST_CONTROL_SOURCE=/home/outsider/.cache/lifeos-daily-text-20261007/background-control-source/LifeOS/install
export LIFEOS_UPGRADE_CONTROL_SOURCE=/home/outsider/.cache/lifeos-daily-text-20261007/hypothesis-helpers-first/lifeos/LifeOS/install
export PYTHONPATH=/home/outsider/Projects/Hermes_agent/LifeOS_plugin:/home/outsider/Projects/Hermes_agent/LifeOS_plugin/tests
/home/outsider/.cache/lifeos-plugin-memory/memory-plugin-test-env/bin/python -W error -m unittest \
  test_memory_morning_brief test_memory_owner_jobs test_memory_owner_job_command test_memory_owner_job_processes \
  test_memory_session_harvest test_memory_proposal_gc test_memory_runtime test_memory_native_response_authority \
  test_memory_sources test_memory_freshness test_memory_telos \
  > docs/verification/2026-10-08-morning-brief/adjacent-gate.txt 2>&1
result=$?
printf '%s\n' "$result" > docs/verification/2026-10-08-morning-brief/adjacent-gate.done
exit "$result"
