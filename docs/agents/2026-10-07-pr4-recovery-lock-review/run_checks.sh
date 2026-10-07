#!/bin/bash
# ABOUTME: Runs bounded selection closure checks against the reviewed PR head.
# ABOUTME: Saves all local test output and an explicit completion marker.
export PATH=/home/outsider/.bun/bin:$PATH
export PYTHONPATH=tests:.:/home/outsider/.cache/lifeos-step1-20261007/prepared-review-final/hermes
export TMPDIR=/home/outsider/.cache/lhc6
export LIFEOS_MEMORY_SOURCE=/home/outsider/.cache/lifeos-step1-20261007/prepared-review-final/lifeos/LifeOS/install
export LIFEOS_HERMES_SOURCE=/home/outsider/.cache/lifeos-step1-20261007/prepared-review-final/hermes
output=docs/agents/2026-10-07-pr4-recovery-lock-review
python=/home/outsider/.cache/lifeos-plugin-memory/memory-plugin-test-env/bin/python
"$python" "$output/probe_failed_launch.py" > "$output/failed-launch.stdout" 2> "$output/failed-launch.stderr"
printf '%s\n' "$?" > "$output/failed-launch.exit"
"$python" -m pytest -q tests/test_installation_selection.py tests/test_selection_profile_isolation.py tests/test_selection_recovery_admission.py tests/test_selection_native_mount.py > "$output/focused-tests.txt" 2>&1
printf '%s\n' "$?" > "$output/focused-tests.exit"
"$python" scripts/check_hook_evidence.py --require-complete > "$output/evidence-check.txt" 2>&1
printf '%s\n' "$?" > "$output/evidence-check.exit"
date -u +'%Y-%m-%dT%H:%M:%SZ' > "$output/.done"
