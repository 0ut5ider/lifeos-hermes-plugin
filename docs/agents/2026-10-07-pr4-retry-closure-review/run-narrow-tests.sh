#!/bin/bash
cd /home/outsider/Projects/Hermes_agent/LifeOS_plugin
export PATH=/home/outsider/.bun/bin:$PATH
export PYTHONPATH=tests:.:/home/outsider/.cache/lifeos-step1-20261007/prepared-review-final/hermes
export TMPDIR=/home/outsider/.cache/lhc6
export LIFEOS_MEMORY_SOURCE=/home/outsider/.cache/lifeos-step1-20261007/prepared-review-final/lifeos/LifeOS/install
export LIFEOS_HERMES_SOURCE=/home/outsider/.cache/lifeos-step1-20261007/prepared-review-final/hermes
export LIFEOS_FRESH_SOURCE=/home/outsider/.cache/lifeos-step1-20261007/installer-review-final
export LIFEOS_TASK_HOOK_PATH=$LIFEOS_MEMORY_SOURCE/hooks/TaskGovernance.hook.ts
/home/outsider/.cache/lifeos-plugin-memory/memory-plugin-test-env/bin/python -m pytest -q -rs tests/test_installation_selection.py tests/test_selection_profile_isolation.py tests/test_selection_retry.py tests/test_selection_recovery_admission.py tests/test_selection_native_mount.py > docs/agents/2026-10-07-pr4-retry-closure-review/narrow-tests.stdout 2> docs/agents/2026-10-07-pr4-retry-closure-review/narrow-tests.stderr
result=$?
printf '%s\n' "$result" > docs/agents/2026-10-07-pr4-retry-closure-review/narrow-tests.exit
printf 'done\n' > docs/agents/2026-10-07-pr4-retry-closure-review/.done
exit "$result"
