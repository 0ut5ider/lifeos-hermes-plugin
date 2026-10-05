# Hook source differences between the two paired clients

Date: 2026-10-05. The paired controls do not run byte-identical hook programs. The native client runs the installed reference LifeOS tree. Hermes runs the prepared LifeOS tree with the compatibility patches that this plugin ships. An [independent review](../agents/2026-10-05-pr3-evidence-review/pr3-evidence-review.md) reports that the unit records did not state this. This page records the measured differences.

The measurement compares `hooks/` in `/home/lifeos-claude-ref/.claude` with `hooks/` in the prepared runtime `/var/tmp/lifeos-paired-context-response-20261005/lifeos` on `.212`. Both trees report LifeOS 7.40.4. 29 files differ.

## Identity text only (15 files)

The reference tree is an installed tree, so the installer has replaced the identity placeholders with the fictional fixture names. The prepared tree keeps the placeholders such as `{{DA_NAME}}`. Every changed line in these files is such a replacement. The check is a line comparison, not a syntax analysis.

`AgentInvocation.hook.ts`, `ConfigEvalFire.hook.ts`, `DriftReminder.hook.ts`, `FormatGate.hook.ts`, `ISAFoldGate.hook.ts`, `PromptProcessing.hook.ts`, `README.md`, `Safety.hook.ts`, `TabState.hook.ts`, `WritingGate.hook.ts`, `handlers/DocCrossRefIntegrity.ts`, `handlers/UpdateCounts.ts`, `lib/safety-classifier.ts`, `lib/tab-constants.ts`, `lib/work-config.ts`.

The list has 14 program files and the `README.md` documentation file.

## Program differences (13 files)

These files differ in program lines. The plugin's LifeOS compatibility patches are the expected cause. This page does not yet map each file to its patch.

| File | Changed lines |
| --- | --- |
| `CheckpointPerISC.hook.ts` | 88 |
| `ModelRungGuard.hook.ts` | 40 |
| `ISAStaleWriteGuard.hook.ts` | 31 |
| `LoadContext.hook.ts` | 30 |
| `TaskGovernance.hook.ts` | 28 |
| `MemoryDeltaSurface.hook.ts` | 19 |
| `lib/learning-readback.ts` | 13 |
| `lib/advisory-readback.ts` | 10 |
| `EventLogger.hook.ts` | 8 |
| `LoadMemory.hook.ts` | 8 |
| `lib/tab-setter.ts` | 4 |
| `KittyEnvPersist.hook.ts` | 3 |
| `MemoryTurnStart.hook.ts` | 3 |

One further file, `lifeos-bridge-capabilities.json`, exists only in the prepared tree. That gives 15 + 13 + 1 = 29 differing files.

## Effect on the claims

A paired case therefore compares stock LifeOS under Claude Code with patched LifeOS under Hermes. That is the product comparison, because the release installs the patched tree. It is not a comparison of one program under two hosts.

Affected units in the ledger:

- Tool logging uses `EventLogger.hook.ts`, which has program differences. Its two clients write different output fields. See the [tool logging record](../verification/2026-10-05-paired-tool-log/README.md).
- Startup context cases use `LoadContext.hook.ts` and both readback libraries.
- The end-of-turn render cases use different `ISARender.ts` files; that tool is outside `hooks/` and is not classified here.
- Version drift, mutation hints, the pre-tool guard, and the loop detector use byte-identical hook files on both sides.
- File hints use an identical `AtlasEventCapture.hook.ts` and a `ConfigEvalFire.hook.ts` that differs in identity text only.

Neither `check_pair` nor the ledger check compares source digests. Each unit's `runtime-check.json` records the digests of the selected hooks for both sides.
