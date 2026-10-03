#!/bin/bash
cd /home/outsider/Projects/Hermes_agent/LifeOS_plugin
export PYTHONPATH=.:tests
export LIFEOS_MEMORY_SOURCE=/home/outsider/.cache/lifeos-plugin-memory/source-gate-20261001-cortex-final/lifeos/LifeOS/install
export LIFEOS_HERMES_SOURCE=/home/outsider/.cache/lifeos-plugin-memory/source-gate-20261001-cortex-final/hermes
/home/outsider/.cache/lifeos-plugin-memory/memory-plugin-test-env/bin/python docs/agents/2026-10-01-memory-fresh-review/raw/probe_dashboard_extra.py > docs/agents/2026-10-01-memory-fresh-review/raw/dashboard-extra.log 2>&1
printf '%s\n' "$?" > docs/agents/2026-10-01-memory-fresh-review/raw/dashboard-extra.done
