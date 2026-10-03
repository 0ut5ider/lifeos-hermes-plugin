#!/bin/sh
# ABOUTME: Runs disposable synthetic memory review controls and saves their results.
# ABOUTME: Uses the owned prepared public sources and records process completion.
cd /home/outsider/Projects/Hermes_agent/LifeOS_plugin || exit 2
export PYTHONPATH=.:tests
export LIFEOS_MEMORY_SOURCE=/home/outsider/.cache/lifeos-plugin-memory/source-gate-20261001-cortex-final/lifeos/LifeOS/install
export LIFEOS_HERMES_SOURCE=/home/outsider/.cache/lifeos-plugin-memory/source-gate-20261001-cortex-final/hermes
closure_raw=docs/agents/2026-10-01-memory-closure-review/raw
for closure_probe in recovery_delta recovery_contracts distinct_delta_latency explicit_context_provenance agent_source_session; do
    /home/outsider/.cache/lifeos-plugin-memory/memory-plugin-test-env/bin/python "$closure_raw/probe_$closure_probe.py" > "$closure_raw/final-$closure_probe.log" 2>&1
    status=$?
    printf '%s\n' "$status" > "$closure_raw/final-$closure_probe.done"
    if [ "$status" -ne 0 ]; then
        printf '%s\n' "$status" > "$closure_raw/final-closure.done"
        exit "$status"
    fi
done
sh "$closure_raw/run-final-targeted.sh"
status=$?
printf '%s\n' "$status" > "$closure_raw/final-closure.done"
exit "$status"
