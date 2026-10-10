# Reproduction commands

Run from `/home/outsider/Projects/Hermes_agent/LifeOS_plugin`.

1. Run `bash docs/agents/2026-10-10-atlas-limits-review/run-native.sh`.
2. Run the projection command below after native completion.
3. Run `bash docs/agents/2026-10-10-atlas-limits-review/run-managed.sh`.
4. Run `bash docs/agents/2026-10-10-atlas-limits-review/run-backup.sh`.
5. Run `bash docs/agents/2026-10-10-atlas-limits-review/run-transport.sh`.
6. Run `bash docs/agents/2026-10-10-atlas-limits-review/run-snapshot-byte.sh`.

```bash
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=. /home/outsider/.cache/lifeos-plugin-memory/memory-plugin-test-env/bin/python docs/agents/2026-10-10-atlas-limits-review/projection-measure.py
```

The review launches the shell supervisors with `setsid`, disconnected stdin, and output files. Each supervisor writes an exit code and a completion marker. Raw native graph and snapshot datasets are synthetic. No test contacts a model endpoint or a server.

The first managed attempt uses a missing convenience method on the fixture. The second starts beyond the projection limit. The third starts exactly below the limit, then accidentally crosses it in the intended near-bound test. Their raw errors remain in `managed-first.*`, `managed-second.*`, and `managed-third.*`. The corrected final managed experiment passes with exit code zero. These are experiment-harness corrections, with no application change.
