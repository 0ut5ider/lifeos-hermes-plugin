# Native proposal state-machine review

Date: 2026-09-30  
Role: Independent code, native integration, and policy reviewer  
Question: Do managed proposal creation, pending and resolved review, manual and automatic decisions preserve permissions, standalone behavior, and retained-context invalidation?  
Model: GPT-6. The exact model variant is not exposed in this agent context.

## Conclusion

Three meaningful findings were confirmed against the initial local-development snapshot and reported with real fixture reproductions. The primary agent fixed all three. The current closure tests and probes verify those fixes. I found no remaining material defect in the bounded proposal state-machine integration reviewed here.

All 48 affected tests passed in the closure snapshot. Additional real-native probes verified five managed transitions, five no-connector native transitions, seven malformed-configuration or raw-write refusals, five runtime-context outcomes, private-note rejection with metadata-only receipt persistence, and three post-forget application refusals.

This conclusion covers the implemented local proposal operations. It does not approve installation activation or claim completion of historical proposal adoption, learning-source coverage, restricted prompts, complete lifecycle handling, installation recovery, or proposal UI controls.

## Findings and verified corrections

### 1. Dangling connector symlink caused unmanaged fallback

Initial severity: high. Status: closed.

The native `hasMemoryAccess()` used `existsSync()` to decide whether to delegate. A dangling connector symlink returned false and selected the unmanaged path. In `raw/probe_dangling_connector.py`, proposal permissions were revoked first. The native accept call correctly refused with the valid connector. After the connector became a dangling link, the same native accept succeeded, changed the target, and left the SQLite proposal marked pending.

This was an invalid but present connector, not intentional absence. Raw initial evidence is in `raw/dangling-connector.jsonl`.

The corrected helper uses `lstatSync()` and treats only `ENOENT` as absence. The delegation then validates file type, symlink status, owner, permissions, version, and command. The closure matrix confirms that a dangling link, directory, public permissions, invalid JSON, unsupported version, and unavailable command all refuse without modifying the target or pending proposal. A raw queue-set request also refuses under a configured connector.

See `closure/probe_native_states.txt`, especially the seven `invalid_connector_case` rows. The matrix catches expected native errors so it can assert that the target and queue remain unchanged. It does not convert those failures into successful operations.

### 2. Applied-elsewhere notes bypassed native text validation

Initial severity: medium. Status: closed.

The new note argument was initially checked only for type and size. An applied-elsewhere decision containing `<private>PRIVATE-NOTE-MARKER</private>` committed the marker into `resolution_note`, native resolved history, and the returned decision body. The actual fixture result is preserved in `raw/decision-text.jsonl`.

The corrected decision path passes the note through the native persistence sanitizer using an idea payload. It rejects invalid or transformed text before reserving an operation. The closure probe confirms:

- The private note returns `rejected`.
- No operation receipt is created for that request.
- The private marker is absent from the native queue.
- A valid synthetic note still commits through the native applied-elsewhere transition.

The current unit regression also rejects control characters and frontmatter injection. See `closure/decision-text-negative.txt` and `closure/proposals-tests.txt`.

### 3. Native row response duplicated proposal bodies in SQLite receipts

Initial severity: medium, violation of the metadata-only receipt invariant. Status: closed.

The initial decision callback returned a complete native row inside the persisted receipt. The same real probe confirmed that SQLite `operations.receipt` contained the proposal edit, rationale, and resolution note. This introduced durable proposal-body copies into the metadata store.

The corrected callback returns a receipt containing only status, reference, destination, creator, writer, and request ID. The native service response assembles its row separately through `proposal_decision_row()` after publication. That helper requires approval or automatic-application permission, checks the committed proposal revision, and reads the verified native row.

The closure probe confirms that a valid decision's durable receipt contains none of the edit, rationale, or note text, while resolved native review still returns the authoritative row. An identical request retry returns the same metadata receipt. The real Bun-to-RPC delegation matrix confirms that native decision callers still receive their expected row response.

See `closure/decision-text-negative.txt`. The original evidence remains in `raw/decision-text.jsonl`.

## State-transition verification

`raw/probe_native_states.py` invokes actual Bun functions in the native proposal module. It uses the actual Python RPC service for managed calls. The same script was rerun after all fixes, with results in `closure/probe_native_states.txt`.

| Requested operation | Native final state | Target behavior | Managed and no-connector cases |
|---|---|---|---|
| Accept | `accepted` | Original edit applied | Both passed |
| Reject | `rejected` | No proposal edit applied | Both passed |
| Edit | `edited` | Alternate text applied | Both passed |
| Applied elsewhere | `applied-elsewhere` | Target unchanged | Both passed |
| Automatic application | `auto-applied` | Original edit applied after threshold check | Both passed |

The probe reads the queue after each transition and verifies the resolved list output. This establishes the expected standalone native behavior for these operations when no connector exists. It is not an exhaustive equivalence test of all unmanaged LifeOS behavior.

The proposal and delegation suites additionally verify:

- Creation produces a pending native reference, not an applied-fact receipt.
- Diverted upgrade outcomes are preserved and skipped by the managed automatic-application branch.
- Creation permission does not imply manual or automatic approval.
- Manual approval permission does not imply `auto_apply` permission.
- Low-confidence proposals fail the configured native threshold check.
- External clients may receive creation and review grants but cannot receive approval grants through client configuration.
- Native direct accept updates the managed revision, and a later stale decision conflicts.
- Revoking review and decision grants affects fresh native reads and decisions.
- Raw apply, mark, and queue-set functions cannot bypass the managed decision path when a connector is present.
- Target content changes before approval produce a conflict instead of an overwrite.
- Identical request retries preserve the recorded result.

The new automatic decision is not exposed as a public manual tool enum. It is reached through the native operation path with its distinct grant and threshold.

## Retained-context invalidation

The runtime generation now includes proposal IDs, revisions, and statuses for accepted, edited, and automatically applied rows. The same transaction that commits a decision updates its proposal revision and status before a later model-call guard compares generations.

`raw/probe_context_states.py`, rerun unchanged into `closure/probe_context_states.txt`, exercised every decision using actual native target changes and real runtime admission:

| Decision | Previously admitted context refused | Fresh context admitted |
|---|---|---|
| Accept | Yes | Yes |
| Edit | Yes | Yes |
| Automatic application | Yes | Yes |
| Reject | No | Yes |
| Applied elsewhere | No | Yes |

Reject and applied-elsewhere do not change the governed target, so the unchanged retained context remains valid in these fixtures. Actual external changes represented by an applied-elsewhere note remain subject to the separate full source/lifecycle coverage gate.

## Forgotten-claim checks

Creation rejects exact retained forgotten or superseded claims through the existing normalized claim guard. The existing regression covers forgetting before proposal creation.

The additional `closure/probe_pending_forget.py` covers a different ordering: queue a proposal first, then forget its source fact, then attempt to apply it. Accept, edit with the forgotten alternate text, and automatic application all return `rejected`; no forgotten claim reaches the target. Results are in `closure/pending-forget.txt`.

These are exact normalized-claim checks. This review does not claim universal semantic paraphrase detection.

## Bounded raw-writer inventory

The TypeScript search is preserved in `raw/native-inventory.txt`; its command is in `raw/commands.txt`.

The searched proposal queue and edit writers resolve as follows:

- `MemorySystem.add()` remains the queue creator and delegates through the governed connector when configured.
- `PULSE/lib/memory-proposals.ts` owns queue publication, marking, and target application. Direct raw queue-set, mark, and apply paths now refuse in managed mode.
- Its public decision helpers resolve a scoped native row and delegate a referenced decision. The isolated backend uses the original native functions under the internal worker flag.
- `MemoryReviewer.dispatchItems()` uses the returned pending reference for managed automatic decisions and skips upgrade diversions. Its original direct apply/mark sequence remains only in the no-connector branch.
- `ProposalDecide.ts` calls the decision helpers; the inspected file does not introduce a second queue writer.

The search also found raw proposal readers in `MemoryStatus.ts`, `MemoryInsights.ts`, `CortexHealth.ts`, and the Pulse memory and menubar modules. These are not additional proposal mutation sites in the inspected inventory. They remain relevant to the explicitly open full source/audience coverage gate. This bounded search is not certification that every native diagnostic, model input, or historical source has been governed.

## Tests

All Python commands used `/home/outsider/.cache/lifeos-plugin-memory/memory-plugin-test-env/bin/python`. Native fixtures used the public managed source under `/home/outsider/.cache/lifeos-plugin-memory/managed-source/LifeOS/install`.

| Suite | Initial review | Final closure | Final raw output |
|---|---:|---:|---|
| Native proposals | 14 passed | 16 passed | `closure/proposals-tests.txt` |
| Native proposal delegation | 5 passed | 6 passed | `closure/proposal_delegation-tests.txt` |
| Runtime admission | 16 passed | 16 passed | `closure/runtime-tests.txt` |
| Memory service | 9 passed | 9 passed | `closure/service-tests.txt` |
| Installed-copy MCP | 1 passed | 1 passed | `closure/mcp-tests.txt` |
| **Total** | **45 passed** | **48 passed** | |

The final suites and all additional probes completed successfully. Expected invalid-configuration errors and rejected operations are captured and asserted by the probes. No model service, production data, or live server was used.

The broader plugin suite and freshly prepared distributed-source matrices reported by the primary agent are not presented as this reviewer's independent results. No further optional tests were run after the primary agent requested finalization. The separate preferences/UI unit, including its newly added failing test, is outside this review.

## Snapshots, commands, and scope limits

The initial sources are preserved as numbered files in `raw/`, with hashes in `raw/hashes.json`. The final reviewed sources are preserved in `closure/`, with starting and ending hashes. `closure/source-drift.json` is empty: the closure sources did not change during the verified runs.

`raw/source-fix-drift.json` records the changes made by the primary agent during review. `closure/patch-verification.json` confirms that top-level and bundled LifeOS memory patches are byte-identical. Exact commands are in `raw/commands.txt` and `closure/commands.txt`.

No implementation files were edited or committed by this reviewer. No live server, credential store, fleet host, production memory, or journal was accessed. Temporary fixtures contain only synthetic proposals, rules, notes, and context metadata. Installation activation remains disabled and was not attempted.

## What deserves Adrian's review

The reviewed proposal transitions now use governed references, keep durable receipts as metadata, reject private resolution notes, and refuse malformed connector states instead of entering the unmanaged path. Applied proposals invalidate retained context in the tested runtime routes. These corrections are independently closed.

The remaining risk sits in the declared integration gates: historical proposal adoption, learning and diagnostic source coverage, restricted prompts, complete conversation lifecycle handling, installation recovery, and UI controls. The tests above establish this local proposal unit's behavior; they do not substitute for those activation checks.
