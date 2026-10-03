# Native memory source inventory, candidates

Date: 2026-09-30. Source: prepared public LifeOS base `5e2f2e8c0abde612da0e99c16c0d07d4ec21b88c` with the distributed patches.

The scan identifies 132 candidate TypeScript, shell, and Python files in `hooks`, `LIFEOS/TOOLS`, and `LIFEOS/PULSE`. The raw reference output contains 555 lines. The scan searches for memory module names, hot-file names, and `MEMORY/` path literals. It does not read installed user records or connect to another server.

`candidate-paths.json` records text mentions of connector and filesystem functions. These are candidates for manual call-path review, not proof that a function executes. The scan can miss dynamically constructed paths, imported helpers, and subprocess commands. It does not establish complete reader or writer coverage.

## Next source checks

1. Trace each registered memory hook through its actual read and write functions.
2. Trace native command-line diagnostics and PULSE consumers.
3. Trace direct writers and subprocesses through the cooperating publication lock and provenance boundary.
4. Pair every relevant path with admitted, restricted, corrected, forgotten, and unavailable cases.
5. Record actual output and persisted bytes before claiming a path is governed.

The initial diagnostic read identifies `MemoryStatus.ts`, `MemoryInsights.ts`, and `CortexHealth.ts` as follow-up candidates. `MemoryStatus.ts` reads hot memory through `MemoryWriter`, but it also reads observability rows directly. Its generic JSONL reader returns the parsed row. A TypeScript result interface does not filter the runtime object. The inventory must establish which fields can reach model or messaging output. This observation does not establish a reproduced leak.

The existing proposal review, source adoption, startup readback, and learning tests remain bounded evidence. Their passing results do not clear all 132 candidates. Lasting-memory ownership remains disabled on running installations.
