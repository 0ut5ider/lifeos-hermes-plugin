# Verification of adoption diagnostic admission

Date: 2026-10-02

Role: Independent reviewer of the final adoption diagnostic correction

Question: Does the diagnostic-path correction mask excluded filenames while preserving safe diagnostics and the prior recovery and retrieval corrections?

Model: GPT-6.1-Sol, high reasoning effort

Reviewed revision: `22745d4f1e3adff4e4c6b7900bf88506d3c89a18`

Parent revision: `eed9bdb745ac56824a4b3e2a3ba08d09e8839cfe`

Repository: `/home/outsider/Projects/Hermes_agent/LifeOS_plugin`

## Conclusion

The exact early-body diagnostic-path variant is closed. Private and normalized forgotten filenames are masked. Safe rejected filenames remain useful.

The prior restore, apply, and registered-source retrieval closure probes still pass. The 21 selected source-label and adoption tests pass with no skips.

One related P2 diagnostic exposure remains. A rejected proposal can return a forgotten filename inside `excluded.reason`. The correction admits only `excluded.path`. This remaining behavior is not introduced by `22745d4`, but it belongs to the diagnostic admission surface under review.

Request a correction to the raw exception diagnostic before claiming that adoption diagnostics exclude forgotten source labels. The primary reviewer is running the complete release gate separately.

## Remaining finding

### P2: Do not return raw proposal target exceptions in adoption diagnostics

Primary location: `lifeos_hook_bridge/memory_adoption.py:160`.

Related locations: `memory_adoption.py:152` and `memory_adoption.py:163`.

Proposal adoption calls `Path.relative_to(memory.root)` on its declared target. If an absolute target is outside that root, Python raises `ValueError`. The exception contains the full target path. The catch block returns `str(error)` in `excluded.reason`.

The new filter validates only each diagnostic's `path` field. For a rejected proposal, that field is the fixed queue path. The dynamic target filename stays in the reason. The filter does not apply native validation or normalized retired-label admission to that reason.

#### Concrete failing scenario

1. The owner forgets the claim `Synthetic retired source label`.
2. The native pending queue contains a proposal whose target is outside the installed memory root.
3. The target filename is `Synthetic_retired_source_label.md`.
4. The proposal's edit and rationale contain safe synthetic text.
5. The owner requests the source adoption preview.

The proposal is correctly excluded. The returned reason still contains the forgotten filename. Native history admission excludes the normalized label. Ownership and external sharing are disabled in this owner fixture.

A stale absolute target from another installation or a malformed queue entry can trigger this path. The probe does not read the foreign target file. It only exercises validation and response construction.

#### Reproduction

Run from the repository with the safe environment in [the command manifest](raw/commands-revision.json):

```sh
/home/outsider/.cache/lifeos-plugin-memory/memory-plugin-test-env/bin/python docs/agents/2026-10-02-sol-diagnostic-closure/raw/probe-foreign-proposal-reason.py
```

This standalone probe uses real native validation and the actual owner preview method. It asserts that the response omits the forgotten label. That assertion fails at the reviewed revision.

Observed output from [the full failure log](raw/foreign-proposal-reason.txt):

```text
normalized_label_excluded: true
preview.records: []
preview.proposals: []
preview.excluded.path: LIFEOS/MEMORY/OBSERVABILITY/pending-proposals.jsonl
preview.excluded.reason: '<synthetic-home>/Synthetic_retired_source_label.md' is not in the subpath of '<synthetic-home>/.claude'
marker_in_response: true
ownership_enabled: false
sharing_enabled: false
AssertionError: Retired filename enters the excluded proposal reason
exit: 1
```

The log preserves the complete synthetic paths. The excerpt above shortens their temporary parent for readability.

#### Impact and limits

A forgotten label returns in an enabled owner review response. The finding does not demonstrate an unauthorized cross-account read, private-markup exposure in this reason, a model request, or external-client delivery.

The foreign target remains excluded and unread. This is a response admission defect, not a target authorization bypass.

#### Minimal suggested fix

Return a fixed diagnostic for a target outside the installed root. Do not use the raw `Path.relative_to` exception as user-facing text. Keep safe source filenames in the dedicated admitted path field. Alternatively, apply admission to every dynamic diagnostic value before returning it.

Add the foreign-target retired-filename case to the diagnostic regression tests. Confirm that the excluded proposal remains visible with a useful fixed reason and without its excluded target label.

## Verified exact correction

The reviewer read the complete `eed9bdb..22745d4` diff. The new filter runs before the preview signature and response. It validates diagnostic paths with native source validation and normalized history admission.

The independent diagnostic matrix creates Knowledge sources with a body that triggers the early retired-claim rejection. Results:

| Source filename | Preview records | Excluded path | Label exposure |
| --- | --- | --- | --- |
| `<private>SYNTHETIC_PRIVATE_REJECTED_LABEL.md` | Empty | `[excluded source]` | False |
| `Synthetic_retired_source_label.md` | Empty | `[excluded source]` | False |
| `safe-rejected-source.md` | Empty | Actual safe relative filename | Preserved as intended |

The matrix also observes the remaining proposal-reason variant described above. [Its full output](raw/diagnostics.txt) preserves all four cases.

## Prior closure verification at this revision

The reviewer reran the prior standalone probes against the frozen reviewed source:

- Restore process death still leaves `restore_stopping`. Recovery preserves the selected program and later memory and profile edits. The baseline stays unchanged. A later restore still refuses changed data.
- Apply process death still leaves `stopped`. Direct recovery ends `rolled_back` and preserves the original program, profile, user data, and baseline.
- The separate real password-session owner fixture still admits dashboard recovery and validates its fresh recovery-bound authorization.
- Private filenames, private frontmatter titles, and normalized forgotten filenames in existing registrations remain absent from canonical, Knowledge, and explicit owner search responses.
- Forgotten dynamic title refusal and operational Knowledge domain semantics remain intact.

[The prior closure output](raw/prior-closures.txt) and [apply closure output](raw/apply-closure.txt) preserve the results. Copied probe sources are saved beside these outputs. The manifest records the exact original probe paths used for execution.

## Results and reproduction records

| Check | Result | Evidence |
| --- | --- | --- |
| `test_memory_source_labels` and `test_memory_adoption` | 21 passed; no skips; exit 0 | [test output](raw/tests.txt) |
| Early diagnostic matrix | Expected path cases pass; remaining reason exposure observed; exit 0 | [matrix](raw/diagnostics.txt) |
| Forgotten proposal target reason assertion | Fails with the expected exposure; exit 1 | [failure output](raw/foreign-proposal-reason.txt) |
| Prior standalone restore and source-label closures | All assertions pass; exit 0 | [closure output](raw/prior-closures.txt) |
| Prior standalone apply and authenticated recovery closure | All assertions pass; exit 0 | [apply output](raw/apply-closure.txt) |
| `git diff --check eed9bdb..22745d4` | Exit 0; no diagnostics | [diff check](raw/diff-check.json) |

No failure was skipped or weakened. The failing assertion is a standalone review probe, not a change to repository tests.

[The command and revision manifest](raw/commands-revision.json) records exact commands, identities, environment paths, and exit codes. [The correction diff](raw/correction.patch) and [source excerpt](raw/diagnostic-source.txt) record the reviewed implementation.

Synthetic HOME and TMPDIR remain under `/home/outsider/.cache/lifeos-plugin-memory/sol-review-followup-home`. The `.cache` directory exists, and the fixture uses real Bun and the pinned public sources. Temporary fixture directories are outside the public report folder.

## Limits and side effects

This was a bounded diagnostic follow-up. The reviewer did not rerun the complete suite or audit new architecture. The primary reviewer is preparing the full gate at this revision.

Native calls, authentication in the test application, filesystem operations, and process kills are real. Systemd liveness, service callbacks, and detached worker launch remain isolated boundaries. The review does not establish live end-to-end recovery, model delivery, or external-client behavior.

The reviewer did not edit implementation or tests, change branches, stop real services, access real credentials or private data, use shared memory or journal tools, contact live servers or GitHub, or start other agents. New artifacts are reports and disposable probes. No external system needs rollback.
