# Publication review correction verification

Date: 2026-10-10. Runtime correction revision: `24e6908e`.

The two independent review findings are corrected. Current owner checks stop further native batch mutations after revocation. Failed checks after publication retain unknown receipts and recovery journals. The caller audit also covers Algorithm summary caches, Conduit insights, LocalIntelligence digests, and LocalIntelligence run logs. Nested conflicts from native rechecks use the same recovery path.

The [summary](verification-summary.json) records **336 distinct selected checks with passing evidence**. It verifies the eight changed runtime file hashes against the final recovery-invariant gate. These results cover the selected publication, reader, job, source preparation, and installation contracts. They do not establish complete repository testing or daily deployment acceptance.

| Gate | Result | Evidence |
|---|---|---|
| Batch publication, staging, native memory, and response authority | 129 pass | [Output](final-batch.txt), [command and source hashes](final-batch.json) |
| Algorithm edits, summaries, native jobs, retries, and readers | 66 pass | [Output](final-algorithm.txt), [command and source hashes](final-algorithm.json) |
| LocalIntelligence readers, publication, run logs, jobs, and lifetime | 36 pass | [Output](final-local.txt), [command and source hashes](final-local.json) |
| Conduit readers, insights, capture, jobs, preparation, and installation | 102 pass, one source preparation skip | [Output](final-conduit-preparation.txt), [command and source hashes](final-conduit-preparation.json) |
| Complete source preparation with real pinned repositories | 4 pass, no skips | [Output](source-preparation-complete.txt), [repositories](source-preparation-repositories.json), [command](source-preparation-complete.json) |
| Final recovery invariants, including changes during native rechecks | 12 pass | [Output](final-recovery-invariants.txt), [command and source hashes](final-recovery-invariants.json) |
| Latest publisher regression after the nested-conflict correction | 50 pass | [Exact command, stdout, and stderr](../../agents/2026-10-10-daily-text-candidate-review/nested-focused-final.json) |
| Conditional Hermes patch removal boundary controls | 6 successful executions with matching responses | [Commands and results](approval-controls.json) |

The gates overlap. Their counts must not be added to obtain a distinct test count. The separate complete preparation gate executes the skipped case successfully with the actual Hermes and LifeOS repositories. The final gates have no failures, errors, or warnings. The final recovery-invariant gate tests the current committed runtime bytes.

## Failure and recovery evidence

The [initial regression](../../agents/2026-10-10-daily-text-candidate-review/fix-regressions-before.json) fails at the expected batch and Algorithm boundaries. The related [cache and digest experiment](../../agents/2026-10-10-daily-text-candidate-review/related-regressions-before.json) includes an observation error in its first LocalIntelligence fixture. The [corrected digest experiment](../../agents/2026-10-10-daily-text-candidate-review/local-regression-before.json) confirms the actual defect. The [Conduit and diagnostic experiment](../../agents/2026-10-10-daily-text-candidate-review/remaining-conflicts-before.json) confirms both remaining callers.

The first correction handles explicit checks after writes. The [native recheck experiment](../../agents/2026-10-10-daily-text-candidate-review/nested-recheck-before.json) then reproduces all three nested planner conflicts. The [diagnostic collection experiment](../../agents/2026-10-10-daily-text-candidate-review/diagnostic-recheck-before.json) reproduces the fourth nested path. The [planner correction](../../agents/2026-10-10-daily-text-candidate-review/nested-recheck-after.json) and [diagnostic correction](../../agents/2026-10-10-daily-text-candidate-review/diagnostic-recheck-after.json) both pass. The final gates above repeat the corrected behavior.

The observation functions call the actual native renderer or publisher before they change a real synthetic file or owner configuration. The tests use real SQLite metadata and authenticated native HTTP for doctrine publication. They preserve the original renderer, authorization checks, and transaction implementation.

Recovery restores unchanged operation destinations and preserves concurrent edits to other sources. Expected-digest recovery refuses to overwrite a later edit to a publication destination and retains its journal for review. Recovery does not rewrite an already completed Git commit. The tests retain the existing actual Git hook, timeout, and staged-file checks.

Three standalone fixtures now omit managed context when they remove the connector. Separate tests retain admitted context and require refusal after connector loss. Runtime access policy remains unchanged.

The [initial sequential run](initial-sequential.txt) completes 333 cases with one failure and one skip. Its [command record](initial-sequential.json) retains the nonzero exit status. That run imports the standalone rejection fixture before its correction. The corrected batch gate passes the rejection and connector-loss cases. The complete preparation gate closes the missing-repository skip. The successful selected gates supersede this diagnostic run.

## Release boundaries

All [36 canonical and packaged patch copies](patch-identity.json) match. Source pins, patch order, and model tiers remain unchanged. The [conditional reduction record](../../../notes/2026-10-10-conditional-hermes-patch-reduction.md) keeps the possible removal as a qualification task.

This work makes no server, Discord, ownership, schedule, or deployment change. The staged archive predates these runtime corrections and must be rebuilt before deployment. Atlas graph initialization, private-channel acceptance, final release packaging and recovery, and daily guest deployment remain separate release gates.
