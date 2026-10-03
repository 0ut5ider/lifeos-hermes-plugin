#!/bin/bash
cd /home/outsider/Projects/Hermes_agent/LifeOS_plugin || exit 1
export LIFEOS_MEMORY_SOURCE=/home/outsider/.cache/lifeos-plugin-memory/source-gate-20261002-mount-release/lifeos/LifeOS/install
export LIFEOS_HERMES_SOURCE=/home/outsider/.cache/lifeos-plugin-memory/source-gate-20261002-mount-release/hermes
export PYTHONPATH=.:tests:$LIFEOS_HERMES_SOURCE
export PYTHONDONTWRITEBYTECODE=1
review_python=/home/outsider/.cache/lifeos-plugin-memory/memory-plugin-test-env/bin/python
review_output=docs/agents/2026-10-02-sol-recovery-admission-review/raw
"$review_python" -m unittest -v test_memory_admin_dashboard > "$review_output/dashboard-suite.txt" 2>&1
printf '%s\n' "$?" > "$review_output/dashboard-suite.exit"
"$review_python" "$review_output/probe_recovery_http.py" > "$review_output/http-probe.txt" 2>&1
printf '%s\n' "$?" > "$review_output/http-probe.exit"
touch "$review_output/validation.done"
