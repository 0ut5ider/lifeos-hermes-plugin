Date: 2026-10-01
Role: Independent executable evidence inventory
Question: How can the measured behavior be rerun?
Model: GPT-6.1-Sol, inherited high reasoning effort.

Working directory for every command:

```sh
cd /home/outsider/Projects/Hermes_agent/LifeOS_plugin
```

The command environment for each Python program is:

```sh
export PYTHONPATH=.:tests
export LIFEOS_MEMORY_SOURCE=/home/outsider/.cache/lifeos-plugin-memory/source-gate-20261001-cortex-final/lifeos/LifeOS/install
export LIFEOS_HERMES_SOURCE=/home/outsider/.cache/lifeos-plugin-memory/source-gate-20261001-cortex-final/hermes
```

Exact reproduction commands, with no omitted program arguments:

```sh
/home/outsider/.cache/lifeos-plugin-memory/memory-plugin-test-env/bin/python docs/agents/2026-10-01-memory-correction-review/raw/probe_hot_neighbors.py > docs/agents/2026-10-01-memory-correction-review/raw/hot-neighbors.log 2>&1
/home/outsider/.cache/lifeos-plugin-memory/memory-plugin-test-env/bin/python docs/agents/2026-10-01-memory-correction-review/raw/probe_schema_provenance.py > docs/agents/2026-10-01-memory-correction-review/raw/schema-provenance.log 2>&1
/home/outsider/.cache/lifeos-plugin-memory/memory-plugin-test-env/bin/python docs/agents/2026-10-01-memory-correction-review/raw/probe_delta_and_grants.py > docs/agents/2026-10-01-memory-correction-review/raw/delta-grants.log 2>&1
/home/outsider/.cache/lifeos-plugin-memory/memory-plugin-test-env/bin/python docs/verification/2026-10-01-memory-pulse-http/probe_authenticated_routes.py > docs/agents/2026-10-01-memory-correction-review/raw/network-auth.log 2>&1
/home/outsider/.cache/lifeos-plugin-memory/memory-plugin-test-env/bin/python docs/verification/2026-10-01-memory-pulse-http/probe_host_mount.py > docs/agents/2026-10-01-memory-correction-review/raw/host-mount.log 2>&1
setsid bash docs/agents/2026-10-01-memory-correction-review/raw/run-regression.sh >/dev/null 2>&1 < /dev/null &
```

The complete unittest module list and output/exit-marker commands are inside run-regression.sh. Source identity uses git status --short, git rev-parse HEAD, and SHA256 of each captured path. Hash JSON retains the exact paths. All five observation/smoke programs exit 0. The expanded regression exits 1. No original probe SyntaxError, setup error, or later rewritten expected result is hidden. The observations record the contract failures directly in JSON.
