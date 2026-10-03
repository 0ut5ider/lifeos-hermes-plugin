#!/bin/bash
cd /home/outsider/Projects/Hermes_agent/LifeOS_plugin
export PYTHONPATH=.:tests
export LIFEOS_MEMORY_SOURCE=/home/outsider/.cache/lifeos-plugin-memory/source-gate-20261001-cortex-final/lifeos/LifeOS/install
export LIFEOS_HERMES_SOURCE=/home/outsider/.cache/lifeos-plugin-memory/source-gate-20261001-cortex-final/hermes
/home/outsider/.cache/lifeos-plugin-memory/memory-plugin-test-env/bin/python -m unittest test_memory_pulse_auth test_memory_dashboard test_memory_preferences test_memory_pulse -v > docs/agents/2026-10-01-memory-pulse-auth-review/raw/tests.txt 2>&1
result=$?
echo "$result" > docs/agents/2026-10-01-memory-pulse-auth-review/raw/tests.done
