#!/bin/bash
cd /home/outsider/Projects/Hermes_agent/LifeOS_plugin
export PYTHONPATH=.:tests
export LIFEOS_MEMORY_SOURCE=/home/outsider/.cache/lifeos-plugin-memory/source-gate-20261001-cortex-final/lifeos/LifeOS/install
export LIFEOS_HERMES_SOURCE=/home/outsider/.cache/lifeos-plugin-memory/source-gate-20261001-cortex-final/hermes
/home/outsider/.cache/lifeos-plugin-memory/memory-plugin-test-env/bin/python -m unittest -v test_memory_native test_memory_curation test_memory_service test_memory_proposals test_memory_diagnostics test_memory_cortex_health test_memory_pulse test_memory_pulse_auth test_memory_runtime test_memory_sharing test_memory_context test_memory_adoption > docs/agents/2026-10-01-memory-fresh-review/primary-validation/regression.log 2>&1
printf '%s\n' "$?" > docs/agents/2026-10-01-memory-fresh-review/primary-validation/regression.done
