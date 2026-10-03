#!/bin/bash
# ABOUTME: Runs existing native governance evidence in owned synthetic fixtures.
# ABOUTME: Records stdout and exit status for the source audit.
cd /home/outsider/Projects/Hermes_agent/LifeOS_plugin || exit 1
export PYTHONPATH=.:tests
export LIFEOS_MEMORY_SOURCE=/home/outsider/.cache/lifeos-plugin-memory/source-gate-20260930-app-startup/lifeos/LifeOS/install
export LIFEOS_HERMES_SOURCE=/home/outsider/.cache/lifeos-plugin-memory/source-gate-20260930-app-startup/hermes
/home/outsider/.cache/lifeos-plugin-memory/memory-plugin-test-env/bin/python -m unittest test_memory_delegation test_memory_sources test_memory_proposal_delegation -v > docs/agents/2026-09-30-memory-native-audit/raw/tests.txt 2>&1
result=$?
printf '%s\n' "$result" > docs/agents/2026-09-30-memory-native-audit/raw/tests.done
exit "$result"
