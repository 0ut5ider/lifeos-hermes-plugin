#!/bin/sh
cd /home/outsider/Projects/Hermes_agent/LifeOS_plugin || exit 1
export PYTHONPATH=.:tests
export LIFEOS_MEMORY_SOURCE=/home/outsider/.cache/lifeos-plugin-memory/source-gate-20260930-cortex-closure/lifeos/LifeOS/install
/home/outsider/.cache/lifeos-plugin-memory/memory-plugin-test-env/bin/python -m unittest test_memory_cortex_health test_memory_diagnostics test_memory_delta.MemoryDeltaTests test_memory_sources test_memory_delegation test_memory_proposal_delegation -v > docs/verification/2026-09-30-memory-cortex-health/closure-tests.txt 2>&1
result=$?
printf '%s\n' "$result" > docs/verification/2026-09-30-memory-cortex-health/closure-tests.done
exit "$result"
