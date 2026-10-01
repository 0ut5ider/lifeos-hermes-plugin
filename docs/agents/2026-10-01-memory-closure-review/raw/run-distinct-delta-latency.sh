#!/bin/sh
# ABOUTME: Runs disposable synthetic memory review controls and saves their results.
# ABOUTME: Uses the owned prepared public sources and records process completion.
cd /home/outsider/Projects/Hermes_agent/LifeOS_plugin || exit 2
export PYTHONPATH=.:tests
export LIFEOS_MEMORY_SOURCE=/home/outsider/.cache/lifeos-plugin-memory/source-gate-20261001-cortex-final/lifeos/LifeOS/install
export LIFEOS_HERMES_SOURCE=/home/outsider/.cache/lifeos-plugin-memory/source-gate-20261001-cortex-final/hermes
/home/outsider/.cache/lifeos-plugin-memory/memory-plugin-test-env/bin/python docs/agents/2026-10-01-memory-closure-review/raw/probe_distinct_delta_latency.py > docs/agents/2026-10-01-memory-closure-review/raw/distinct-delta-latency.log 2>&1
status=$?
printf '%s\n' "$status" > docs/agents/2026-10-01-memory-closure-review/raw/distinct-delta-latency.done
exit "$status"
