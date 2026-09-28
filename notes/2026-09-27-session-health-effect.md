# SessionEnd memory health effect

Date: 2026-09-27

The installed `MemoryHealthGate.hook.ts` invokes the installed `MemoryHealthCheck.ts` on SessionEnd. On isolated `.212`, the bridge dispatched this hook with `CORTEX_HEALTH_ROOT` set to a disposable directory. The check wrote one row to that directory's `LIFEOS/MEMORY/OBSERVABILITY/memory-health.jsonl`.

The fixture intentionally lacked normal LifeOS data, so it verifies the native invocation and log write, not a healthy status. No live LifeOS health record was changed by the probe.
