# Memory history repair review

Date: 2026-09-30

Role: Independent bounded code and behavior reviewer

Question: Does retained chat-history projection safely repair native fact changes while preserving route, identity, permissions, protocol identifiers, and persisted transcript content?

Model: GPT-6. The exact model variant is not exposed in this agent context.

## Result

**One confirmed high-priority defect in the reviewed initial implementation: repair can overwrite concurrent admission state, weakening later retained-context revocation.** The normal focused suite passed. The defect required a controlled concurrency probe and is not covered by that suite.

The primary has acknowledged the finding and started a fix. This report closes the initial review evidence, not review of the subsequent fix. A separate closure run is required against a stable updated snapshot.

## Confirmed finding: stale session registry publication

Location in the reviewed snapshot: `memory_runtime.py`, `_check_call`, the early `states = self._states()` and later `publish(self.state_path, ...)` after a generation refresh.

The repair path reads the whole session registry before acquiring the native cooperating lock. It later modifies and publishes that old dictionary under the lock. Another legitimate admission between those steps can be silently removed.

### Reproduction and consequence

The saved probe performs these real operations in a disposable native fixture:

1. Admit session `session`, then forget a native fact to require a generation refresh.
2. Start a repair in a second thread. A Python trace callback pauses the real function immediately after it reads the registry. The snapshot contains only `session`.
3. Admit `concurrent-session` normally. The persisted registry now contains both sessions.
4. Resume repair. It succeeds, dispatches its projected request, and republishes the stale dictionary.
5. The registry now contains only `session`; `concurrent-session` is lost.
6. Clear process-local binding and disable ownership through the actual configuration API.
7. Call the real request guard for `concurrent-session`. It returns successfully because no bound, inherited, or persisted retained context remains visible for that session.

Exact observed data:

```text
repair_snapshot_sessions: [session]
sessions_after_concurrent_admit: [concurrent-session, session]
repair_errors: []
sessions_after_repair: [session]
inactive_retained_session_check: allowed
```

The trace callback controls scheduling only. It does not replace policy evaluation, file reads, native mutation, locks, state publication, or admission logic. The probe validates the guard-level consequence and does not send an HTTP request after disabling ownership. This can also cause ordinary session availability failures before revocation, because a legitimate admission record disappears.

Reproduction: `raw/probe_state_race.py`. Full output: `raw/state-race.txt`.

Correction direction: read and validate the current registry under the same cooperating lock used for repair publication, then merge the updated session into that current state. Revalidate the saved stamp after acquiring the lock. The primary is implementing this; I made no code changes.

## Independent verification

The focused suite passed **59 tests in 99.729 seconds**, with no failures or skips:

| Module | Tests |
| --- | ---: |
| test_memory_agent | 4 |
| test_memory_history | 9 |
| test_memory_runtime | 25 |
| test_memory_model_calls | 10 |
| test_hermes_memory_provider | 7 |
| test_memory_host | 4 |

The required-system-instruction case also passed separately in 0.428 seconds. That is a repeat of one of the 59 cases, not a 60th distinct test.

The evidence driver uses the unchanged test methods and saves successful full-agent outcomes and observed HTTP requests. Tests and raw captures are under `raw/`. No implementation was mocked by the new full-agent or concurrency probes. Existing provider tests include environment patching and bounded host dispatch callbacks; their scope is narrower than the full-agent HTTP cases.

### What the successful cases establish

- Correction and forget each execute an actual three-request AIAgent turn through the installed plugin and real model SDK against localhost HTTP.
- The second model request contains the retrieved native claim. The third excludes it and includes the actual mutation receipt. The final response reports the committed reference.
- Native recall returns the replacement after correction and no matching fact after forget.
- The returned transcript still contains the original claim, demonstrating request projection without transcript erasure.
- Structured tool content and JSON arguments are projected while tool call IDs and the tested reference/request identifiers remain stable.
- Old user turns are filtered; the latest user quote remains permitted under this implementation's role-based exception.
- Required system and developer instructions are not silently removed. A retired claim in those instructions is refused.
- A changed permission policy, changed installed prompt, changed authenticated author, and changed destination are not accepted as a fact-only refresh.
- The final admission guard refuses reintroduced retired history in the exercised runtime case. Inspection confirms the real host runs admission after the execution-middleware chain.
- The effective extra_body chat messages are projected while unrelated request options remain intact.
- Lazy history containers are refused without consumption in the tested case.

These results do not invalidate the concurrency finding: none of those tests interleaves registry reads, admission, and repair publication.

## Existing failure evidence

The parent supplied `capture-before.txt` and `capture-before-structured.txt`; copies are preserved with a `primary-` prefix under `raw/`.

The structured capture establishes the actual earlier behavior: native correction or forgetting commits, then the host cannot complete its final model request because the context generation is invalidated. The host reports a failed turn and retries the denied request. That is distinct from the earlier fixture stdout parsing problem. I did not count either parent capture as an independent test or reproduce the old implementation during this review.

## Snapshot and subsequent changes

Base repository HEAD is `6bf39be` on `feature/lifeos-memory`. Initial reviewed files and SHA-256 hashes are preserved in `raw/source-hashes.json`; the reviewed runtime hash is `0d1afa70cfb157f1e790e7403bdd62fd1b2bafbcaead22d69335825e0ab5d122`.

The required-instruction safety change was already present in the actual saved memory_history.py snapshot and the nine-case history suite. During review the primary subsequently changed memory_runtime.py and test_memory_agent.py to address findings and add coverage. `raw/source-changes.json` records those changes, with later snapshots retained separately. Those later changes are not declared reviewed by this report.

The primary also identified a separate concern: native LoadMemory output can be appended to the latest user message, which this implementation exempts as user-authored content. The primary is adding a real hook and full-agent reproduction. I have not independently confirmed that path in this review, so it is a clearly attributed open issue rather than a second independently verified finding.

## Commands and safety

Exact commands and retained probe scripts are in `raw/commands.txt`. All runs use the complete `memory-plugin-test-env` Python, `PYTHONPATH=.:tests`, and the owned app-startup prepared Hermes and LifeOS sources. Native records, profiles, configuration changes, and local HTTP endpoints are synthetic fixtures.

I loaded coding-rules and experiment-method. I made no implementation edits, commits, live Hermes imports, account changes, SSH connections, or memory/journal calls.

## Open scope and review priorities

Resume, changed installed SOUL, compression rotation, Responses repair, restricted projection, and ownership activation remain open. The tests retain denial checks for changed SOUL but do not implement or prove its automatic repair. Historical transcripts retain their original content; this unit does not erase backups or prove semantic removal of paraphrases.

Adrian should review closure evidence for the concurrency correction and the primary's native-recall/latest-user issue before treating this unit as complete. Full lifecycle, source inventory, and delivery guarantees remain separate gates.
