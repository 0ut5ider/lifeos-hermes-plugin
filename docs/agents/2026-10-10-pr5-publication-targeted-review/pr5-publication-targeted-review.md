# PR 5 publication targeted review

Date: 2026-10-10.
Role: Independent code reviewer.
Question: Do the final publication corrections preserve current authority and recoverable state before receipt finalization?
Model: GPT-6.1-Sol, inherited.

Reviewed revision: `cc14475fe36cf170d0afcffb1208b38044dfccaf`.
Original review revision: `bf53c16dd23d72c9824843cbb85f31db5a48e723`.
Pull request: https://github.com/0ut5ider/lifeos-hermes-plugin/pull/5.

## Recommendation

Hold the merge for one reproduced P2 correctness finding. The authority corrections and tested source-conflict corrections pass independently. Destination changes before receipt finalization still bypass those corrections in three publisher families.

I do not change runtime code, tests, server configuration, Discord, source pins, Git history, or deployment state. This review writes reports, command records, and isolated synthetic probes only.

## P2: Verify each published destination before committing its receipt

Primary locations:

- `lifeos_hook_bridge/memory_algorithm_summary.py:139-147`.
- `lifeos_hook_bridge/memory_local_refresh.py:174-188`.
- `lifeos_hook_bridge/memory_conduit_insight.py:173-182`.

The post-write checks compare unchanged inputs and authority. They exclude published destinations from those comparisons. They do not separately require destination bytes to equal the bytes that this operation publishes before returning `committed`.

Algorithm excludes the cache from its `inputs` field. LocalIntelligence and Conduit explicitly remove all publication paths from their `untouched` source checks. A valid later owner edit made after the actual write can therefore become the accepted post-publication snapshot.

`NativeMemory._operation` updates the receipt and completes the enclosing transaction when the callback returns `committed`. The transaction removes the recovery journal. Expected publication digests do not verify a successful publication. They protect recovery only when an unknown receipt and journal survive.

The probes call the original publisher, then modify a real synthetic publication destination before the callback returns. They use actual native planners, actual SQLite metadata, and actual file publication. They retain all source and authorization checks.

| Publisher | Actual later destination edit | Observed response and persisted state |
| --- | --- | --- |
| Algorithm summary | Replace the published operational-rules card markdown with another valid owner cache value | `ok=true`; receipt `committed`; journal absent; requested cache value absent; later cache value preserved |
| LocalIntelligence digest | Replace the dated digest news title after its actual write | `ok=true`; receipt `committed`; journal absent; dated digest contains the later title; both latest copies contain the requested title |
| Conduit insight | Change the generated timestamp in the just-published valid insight | Delivery refuses with `Conduit insight destinations change before delivery`; receipt already `committed`; journal absent; initialized configuration remains |

Fresh transactions after the LocalIntelligence and Conduit probes succeed and retain the committed receipts. They cannot recover the incomplete operation because no journal remains. The later owner edit remains in place. This finding concerns false success and premature finalization, not overwriting that edit.

Conduit does compare destination bytes at `memory_conduit_insight.py:190-192`. That check runs after `_operation` completes, when the publication is no longer recoverable. Its refusal proves that moving only the response check cannot close the defect.

### Required correction and done state

Before each affected callback returns `committed`, verify every destination against the operation's exact expected bytes or digests. Include every member of a multi-file publication group. Keep source and authority checks intact. A mismatch after any write must raise the recoverable `MemoryUnavailable`, rather than an ordinary finalized `MemoryConflict`.

Add regressions that make actual valid destination edits after publication, while the callback remains active. Require a refusal, an unknown SQLite receipt, and a retained journal. Then call a fresh transaction. Expected-digest recovery must refuse to overwrite the changed destination and keep the journal. No other group member should be restored before the group precheck succeeds.

Existing source-change tests cannot establish this done state. Their concurrent edits target input files, so the unchanged-input comparisons catch them. The new destination probes exercise files that those comparisons exclude.

### Reproduction evidence

- `probe_destination.py` and `destination-probe.json`: Algorithm summary, exit 0, no stderr. The diagnostic records the defective state explicitly.
- `probe_destination_families.py` and `destination-families.json`: LocalIntelligence and Conduit, exit 0, no stderr, 3.959 seconds.
- Both probes run at the reviewed revision with the exact prepared-source environments recorded in their JSON files.
- The primary agent independently confirms all three probe states under `primary/`. Those files belong to the primary agent.

## Independent verification

| Gate | Result | Scope |
| --- | --- | --- |
| Recorded final recovery invariants | 12 pass; exit 0; 42.266 seconds | Batch revocation, nested source conflicts, explicit post-write conflicts, changed diagnostic destinations |
| Supporting controls | 47 pass; exit 0; 28.149 seconds | Staging, connector-loss refusal, standalone behavior, expected-digest recovery, response authority |
| Knowledge connector controls | 2 pass; exit 0; 0.100 seconds | Managed connector-loss refusal and standalone native mining |

These are 61 distinct executed tests. Their output contains no warnings, failures, or errors. Their passing results do not cover the reproduced destination finalization gap.

`recovery.json`, `controls.json`, and `knowledge-controls.json` record exact commands, environment overrides, exit codes, revision, and elapsed duration. The recovery and controls records also retain source hashes. Standard output and standard error are separate files for the detached gates. Knowledge output is embedded in its JSON record. Numeric `.done` files identify completed detached gates.

`review-identity.json` records all eight changed runtime files and all ten changed test files. `reviewed-diff.json` preserves their actual diff. `supporting-source.json` preserves the inspected operation, transaction, service, and affected publisher code. `native-source-identity.json` retains the actual prepared source manifests and their hashes.

The authority additions check later file publications, both Knowledge record updates, deletions, and final batch receipt construction. The revocation tests alter actual owner configuration and inspect unknown receipts and retained journals. The nested conflict conversions correctly keep `MemoryConflict` from reaching ordinary receipt finalization after the tested writes.

The standalone fixture changes preserve policy. They remove managed context when exercising standalone compatibility. Separate tests retain admitted context and require refusal after connector loss. The independent controls pass both forms.

## Limits

Recovery does not rewrite an already completed native Git commit. The existing correction documentation states this limit. This review does not propose rewriting history.

Legacy batch journals without expected digests preserve differing bytes in private recovery copies before restoring original active files. Expected-digest journals refuse restoration when a destination contains later owner bytes. This existing distinction remains unchanged.

The review does not establish complete repository testing or daily release acceptance. Atlas initialization, private-channel acceptance, final packaging and recovery, daily guest deployment, voice, migration, and patch-reduction architecture remain outside this review. Their accepted release deferrals do not create additional code-merge findings.

Only the reproduced destination finalization finding blocks my merge recommendation. After a correction satisfies the stated done state and passes the relevant regressions, this review does not call for another broad review round.
