# Memory review corrections

Date: 2026-10-05. A [GPT-6 review](../../agents/2026-10-05-pr3-memory-modules-review/pr3-memory-modules-review.md) of the lasting-memory modules reports three high findings. This unit corrects two. Production on `.212` stays unchanged, and lasting memory is disabled there.

| Finding | Reproduction | Correction |
| --- | --- | --- |
| A client call that is in progress finishes after revocation. | Four new tests revoke or narrow the grant during a search, a read by reference, and a write. Before the correction, each call returns the fact or commits the write ([revocation-before.txt](revocation-before.txt)). | The service checks the client grant again before it returns a result. A write with `lifeos_memory_remember` also checks the grant inside the transaction before publication. A changed grant gives a rejected result without data. |
| Recovery overwrites a later owner edit without a copy. | Two new tests edit or create the destination after the journal ([recovery-before.txt](recovery-before.txt)). | Before recovery restores a destination, it keeps every file whose bytes differ from the journal original. The copies and a manifest go to `recovery-preserved/` in the private state directory. |

The final gate passes 103 tests ([after.txt](after.txt)).

## Limits

- Correction, forget, and proposal calls have no check inside their transaction. A revocation during such a call withholds the result, but the write can already be committed.
- Recovery cannot tell an interrupted write from an owner edit. It therefore keeps the bytes in both cases, and the preserved directory has no cleanup.

## Third finding: not corrected

The review reports that managed HTTP mode is lost when both marker files are absent after a restart. The design already has a persistent marker, `memory-http.json`, separate from the connector file. Existing tests cover the loss of the connector alone. The reported case needs the loss of both files, which is the loss of the whole configuration directory. A stock installation without the plugin has the same file state. A second marker in another directory would cover that case, and it needs a decision, because the return workflow must then remove that marker too. The primary agent rates this finding lower than the review does.
