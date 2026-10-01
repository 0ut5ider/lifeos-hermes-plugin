#!/bin/bash
# ABOUTME: Runs independent memory regression against owned prepared public fixtures.
# ABOUTME: Writes the full outcome and exit marker to this review's evidence directory.
cd /home/outsider/Projects/Hermes_agent/LifeOS_plugin || exit 1
export PYTHONPATH=.:tests
export LIFEOS_MEMORY_SOURCE=/home/outsider/.cache/lifeos-plugin-memory/source-gate-20261001-cortex-final/lifeos/LifeOS/install
export LIFEOS_HERMES_SOURCE=/home/outsider/.cache/lifeos-plugin-memory/source-gate-20261001-cortex-final/hermes
/home/outsider/.cache/lifeos-plugin-memory/memory-plugin-test-env/bin/python -m unittest -v test_memory_native test_memory_curation test_memory_service test_memory_proposals test_memory_diagnostics test_memory_cortex_health test_memory_pulse test_memory_pulse_auth test_memory_runtime test_memory_sharing test_memory_context test_memory_adoption test_memory_preferences test_memory_dashboard test_memory_authorization test_memory_archive test_memory_sources test_memory_history test_memory_delta test_memory_agent test_memory_children test_memory_delegation test_memory_proposal_delegation test_memory_review test_memory_mcp test_memory_ssh test_hermes_memory_provider > docs/agents/2026-10-01-memory-correction-review/raw/regression.log 2>&1
printf '%s\n' "$?" > docs/agents/2026-10-01-memory-correction-review/raw/regression.done
