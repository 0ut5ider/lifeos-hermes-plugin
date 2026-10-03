#!/bin/bash
cd /home/outsider/Projects/Hermes_agent/LifeOS_plugin
export PYTHONPATH=.:tests
export LIFEOS_MEMORY_SOURCE=/home/outsider/.cache/lifeos-plugin-memory/source-gate-20260930-cortex-closure/lifeos/LifeOS/install
/home/outsider/.cache/lifeos-plugin-memory/memory-plugin-test-env/bin/python -m unittest test_memory_cortex_health test_memory_diagnostics test_memory_delta.MemoryDeltaTests test_memory_sources test_memory_delegation test_memory_proposal_delegation -v > docs/agents/2026-09-30-memory-cortex-health-review/closure/raw/tests.txt 2>&1
result=$?
echo "$result" > docs/agents/2026-09-30-memory-cortex-health-review/closure/raw/tests.done
exit "$result"
