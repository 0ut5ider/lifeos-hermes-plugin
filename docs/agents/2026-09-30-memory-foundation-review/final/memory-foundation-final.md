Date: 2026-09-30
Role: Independent reviewer, final bounded foundation and recovery verification
Question: Do the four recovery fixes address the confirmed failures, and do the edited paths introduce a meaningful remaining defect?
Model: GPT-6 session model. The exact deployed model variant is not exposed to this reviewer.

# Final foundation verification

The four reviewed recovery defects now pass independent verification. All 26 tests pass, and the ten prior foundation probes complete with corrected outcomes. One concrete regression remains in project-section parsing: an allowed Markdown heading can make a newly committed fact immediately unreadable.

This report applies to the source snapshots in `raw/reviewed-*`, identified by `raw/reviewed-hashes.json`. Later changes to the shared checkout are outside this verification.

## Remaining finding: accepted project content can conflict with the native section parser

Priority: Medium.

Location: `lifeos_hook_bridge/memory_access.py`, `NativeMemory._content`, the search for `"\n## Appended "`.

The new complete-section check treats any line starting with `## Appended ` as the next native section boundary. Native validation allows that Markdown heading within fact content. A new fact can therefore pass validation, save, receive a committed reference, and then fail its first recall.

The `allowed_markdown_heading_conflicts_with_section_parser` probe saves this synthetic content:

```text
Synthetic first paragraph
## Appended experiment notes
Synthetic second paragraph
```

The save returns `committed`. Immediate recall raises `MemoryConflict: The referenced fact changed outside its recorded revision`. No external writer, crash, or manual mutation is involved. The native file still contains the acknowledged fact. The reader incorrectly truncates its section at the user-supplied heading.

Identify native section boundaries unambiguously, using the full native envelope or stored section identity. If the implementation reserves a delimiter instead, validate and reject it before native publication. A committed record must be readable through the same access layer.

This defect was reported to the primary agent with the exact probe and raw result. No additional broad design audit was performed.

## Verified recovery fixes

| Reviewed failure | Independent result |
| --- | --- |
| Native child publishes after Python parent dies | The child retains the recovery lock. Recovery waits until native publication finishes, restores the original rule, and a later acknowledged fact survives. |
| Journal routes a different path from sanitized publication | The private title is rejected before routing. No native knowledge file is created. |
| Crash before journal preparation leaves an unknown reservation | Same-key retry after the injected exit commits and recalls one fact. No abandoned unknown reservation remains. |
| Changed project body retains an obsolete prefix | Correction through the original reference returns conflict. |

The surviving-child regression test passed with its nonblocking flock assertion. The independent scheduling probe also passed after modification to release the paused child asynchronously. It kills the Python parent, starts recovery while the child remains alive, then releases the child. Final native memory contains the original rule and the later acknowledged rule. Recall returns both references. The former orphan replacement is absent.

The code review confirms that one cooperating lock now spans snapshot preparation, reservation commit, native publication, receipt commit, and cleanup. The `ContextVar` supplies the active descriptor to `subprocess.run(pass_fds=...)`. The supported native worker performs its publication synchronously. This verification does not establish a lock protocol for arbitrary additional child writers.

Other independently repeated outcomes:

- An exit after receipt commit preserves the committed fact and its receipt on restart.
- An interrupted hot correction restores the original reference before retry.
- The correction retry then commits and recalls its replacement.
- The earlier privacy, malformed-input, Unicode, duplicate-identity, reactivation, title-binding, and stale-quotation probes retain their corrected outcomes.

## Test evidence

Command: `python -m unittest discover -s tests -p 'test_memory*.py' -v`.

Result: 26 tests passed in 12.904 seconds. No tests were skipped. Full output is in `raw/tests-26.txt`.

The prior foundation diagnostic script completed all ten cases. The final diagnostic script completed seven cases: six establish fixed recovery/reference behavior, and one demonstrates the remaining heading parser regression. The diagnostic scripts report observations rather than acting as passing regression assertion suites.

The final script loads the earlier recovery probe definitions without executing their top-level runs. It updates the postcommit crash injection for the single-transaction implementation, rejects the sanitized-title case through the public operation, and releases the native-child gate asynchronously. Those adaptations prevent stale diagnostic assumptions from creating a deadlock or claiming an injection occurred when it did not.

## Scope and limits

All data is synthetic and stored in temporary fixture roots. The tests use actual Bun and native LifeOS tools. No production memories, logs, remote runtime, configuration, memory service, or journal service were accessed. No implementation code was changed by this reviewer.

The review verifies the cooperating foundation and process-crash recovery at the tested boundaries. It does not verify unbridged native writers, provider integration, MCP access, model-input privacy, UI, backup orchestration, release readiness, or host power-loss behavior. The added publication fsync calls were inspected, but no power-loss experiment was performed.

Artifacts:

- `raw/tests-26.txt`: complete test output.
- `raw/foundation-probes.jsonl`: all ten prior foundation results.
- `raw/probe_final.py`: final bounded diagnostic script.
- `raw/probe-results.jsonl`: all seven final results.
- `raw/reviewed-*`: source snapshots.
- `raw/reviewed-hashes.json`: source hashes.
- `raw/commands.txt`: exact execution commands.

The remaining review item is the project-section parser. Resolve the accepted-heading collision and confirm that the newly saved fact is immediately recallable. The four requested recovery fixes have passed this bounded review.
