#!/usr/bin/env bash
# ABOUTME: Runs the fixed native type and adjacent preparation and editor checks.
# ABOUTME: Records the dashboard build and completion status for detached execution.
set -u
cd /home/outsider/Projects/Hermes_agent/LifeOS_plugin || exit 1
export PATH=/home/outsider/.bun/bin:$PATH
export LIFEOS_MEMORY_SOURCE=/home/outsider/.cache/lifeos-daily-text-20261007/frontend-types-second/lifeos/LifeOS/install
export LIFEOS_HERMES_SOURCE=/home/outsider/.cache/lifeos-daily-text-20261007/frontend-types-second/hermes
export LIFEOS_PREPARE_HERMES_REPO=/home/outsider/.cache/lifeos-daily-text-20261007/channel-sources/hermes
export LIFEOS_PREPARE_LIFEOS_REPO=/home/outsider/.cache/lifeos-daily-text-20261007/channel-sources/lifeos
export LIFEOS_HARVEST_CONTROL_SOURCE=/home/outsider/.cache/lifeos-daily-text-20261007/background-control-source/LifeOS/install
export PYTHONPATH=$PWD:$PWD/tests
/home/outsider/.cache/lifeos-plugin-memory/memory-plugin-test-env/bin/python -W error -m unittest -v test_native_frontend_types test_memory_telos_editor test_patch_bundle test_prepare_sources > docs/verification/2026-10-08-frontend-types/adjacent-gate.txt 2>&1
result=$?
printf '%s\n' "$result" > docs/verification/2026-10-08-frontend-types/adjacent-gate.done
if [ "$result" -ne 0 ]; then exit "$result"; fi
cd "$LIFEOS_MEMORY_SOURCE/LIFEOS/PULSE/Observability" || exit 1
NEXT_TELEMETRY_DISABLED=1 bun run build > /home/outsider/Projects/Hermes_agent/LifeOS_plugin/docs/verification/2026-10-08-frontend-types/build.txt 2>&1
result=$?
printf '%s\n' "$result" > /home/outsider/Projects/Hermes_agent/LifeOS_plugin/docs/verification/2026-10-08-frontend-types/build.done
exit "$result"
