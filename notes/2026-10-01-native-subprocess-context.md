# Native subprocess context must use the current environment

Date: 2026-10-01. Question: Does a long-lived Bun process pass a changed caller context to the governed memory subprocess?

The first context-builder fixture assigns `LIFEOS_MEMORY_CONTEXT` after module import. The owner control returns empty hot memory. A direct probe shows that `process.env` contains the approved context, but a real `spawnSync` child receives no context. An initially bound owner process has the opposite problem: deleting its context does not remove that context from the child environment.

Two isolated native access tests reproduce both directions. Both fail in `docs/verification/2026-10-01-memory-context/child-environment-before.txt`. This defect affects the native connector, before the context builder can enforce caller access. The correction supplies `env: {...process.env}` to the connector's `spawnSync` call. Each child then receives the caller metadata at the time of the operation.

The initial twelve-case builder run includes owner-control failures caused by this defect. It does not prove the cache behavior. The separate run after the environment correction isolates the cache and raw identity reader. Tests must establish their positive owner control before their denial assertions can identify the intended boundary.
