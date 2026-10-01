#!/bin/sh
# ABOUTME: Verifies corrected memory contracts in disposable synthetic homes.
# ABOUTME: Saves independent native probes, a focused gate, and process completion markers.
cd /home/outsider/Projects/Hermes_agent/LifeOS_plugin || exit 2
export PYTHONPATH=.:tests
export LIFEOS_MEMORY_SOURCE=/home/outsider/.cache/lifeos-plugin-memory/source-gate-20261001-cortex-final/lifeos/LifeOS/install
export LIFEOS_HERMES_SOURCE=/home/outsider/.cache/lifeos-plugin-memory/source-gate-20261001-cortex-final/hermes
closure_raw=docs/agents/2026-10-01-memory-closure-review/raw
closure_python=/home/outsider/.cache/lifeos-plugin-memory/memory-plugin-test-env/bin/python
for closure_probe in recovery_delta recovery_contracts distinct_delta_latency corpus_instrumentation explicit_context_provenance agent_source_session; do
    "$closure_python" "$closure_raw/probe_$closure_probe.py" > "$closure_raw/closure-0400794-$closure_probe.log" 2>&1
    status=$?
    printf '%s\n' "$status" > "$closure_raw/closure-0400794-$closure_probe.done"
    if [ "$status" -ne 0 ]; then
        printf '%s\n' "$status" > "$closure_raw/closure-0400794.done"
        exit "$status"
    fi
done
"$closure_python" -m unittest -v test_memory_delta.MemoryDeltaTests.test_distinct_hot_capacity_finishes_within_registered_hook_timeout > "$closure_raw/closure-0400794-isolated-cap.log" 2>&1
status=$?
printf '%s\n' "$status" > "$closure_raw/closure-0400794-isolated-cap.done"
if [ "$status" -ne 0 ]; then
    printf '%s\n' "$status" > "$closure_raw/closure-0400794.done"
    exit "$status"
fi
"$closure_python" -m unittest -v test_memory_native test_memory_archive test_memory_curation test_memory_authorization test_memory_delegation test_memory_delta test_memory_cortex_health test_memory_service test_memory_proposal_delegation test_memory_agent test_memory_mcp > "$closure_raw/closure-0400794-targeted.log" 2>&1
status=$?
printf '%s\n' "$status" > "$closure_raw/closure-0400794-targeted.done"
printf '%s\n' "$status" > "$closure_raw/closure-0400794.done"
exit "$status"
