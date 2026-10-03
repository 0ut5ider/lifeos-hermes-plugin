# Native memory permission closure review

Date: 2026-09-30  
Role: Independent bounded code and synthetic integration reviewer  
Question: Do the two adjacent permission fixes close the restricted-project history and private-entity duplicate defects without regressions in the reviewed operations?  
Model: GPT-6. The exact model variant is not exposed in this agent context.

## Conclusion

Both findings from the native follow-up review are closed in their reproduced cases. I found no additional meaningful defect in this bounded inspection of the changed duplicate-selection and history-admission operations.

The full memory suite passes: 61 tests in 40.168 seconds, process exit 0, no skips reported. Both earlier probe scripts ran unchanged and completed successfully. Three additional synthetic cases confirmed visibility preservation for a fully authorized owner, the reverse correction direction, and rejection of stale native duplicate content.

This closes the two reviewed permission findings. It does not approve activation or claim completion of provider integration or proposal approval.

## Changes inspected

### Unlabeled history requires an unrestricted read scope

`filter_history()` now excludes an unlabeled source unless the scope contains all three native categories and wildcard project access. This addresses the missing project dimension in the previous guard.

The unchanged follow-up probe saved a fact under project `other`, configured the native caller for project `lab`, and built the actual reviewer prompt with a historical exchange containing that fact. Direct recall remained empty, and the reviewer prompt now contained zero exchanges. The original project-only personal-history probe also continued to exclude its exchange.

### Duplicate selection preserves the archive visibility class

The new `_duplicate()` selects active candidates with matching content digest, category, and project. It then checks the candidate's write grant, requires the private-entity classification to match the destination, and verifies the current native content before returning a reference. Both `remember()` and `correct()` use this helper.

The unchanged follow-up probe now creates an accessible public record instead of reusing the private People reference. A later public correction returns the accessible public record. Reads of both returned references succeed. The original public record being corrected is superseded as expected. Direct project-only native People writes remain rejected.

The visibility comparison matters independently of the caller's present permissions. A separate probe used the fully authorized owner to save public content matching an existing People record. The public and private references remained distinct, and a project-only reader could read only the public reference.

A reverse-direction probe corrected a private Companies record to content already present in a public Research record. The correction created a distinct private reference. The owner could read it, and the project-only reader could not. This confirms that a caller with both permissions cannot accidentally erase the destination's private classification through duplicate reuse.

A stale-content probe changed a synthetic native archive section outside the metadata index, then submitted a new request for the indexed content. Duplicate selection returned `conflict` rather than acknowledging stale content as unchanged. The externally changed synthetic section remained intact.

## Verification results

| Verification | Result |
| --- | --- |
| Full `test_memory_*.py` gate | 61 tests passed in 40.168 seconds. |
| Original eight-case native probe script | Completed unchanged, exit 0; results inspected. |
| Follow-up two-case probe script | Completed unchanged, exit 0; both defects now show the corrected outcomes. |
| Owner public/private duplicate separation | Passed with real native publication and distinct references. |
| Private correction matching a public duplicate | Passed; replacement remains private. |
| Duplicate requires current native content | Passed; stale section returns conflict. |
| Related-link archive reference preservation | Original probe still reads both sections successfully. |
| Person correction crash and recovery | Original child exits at the publication boundary; recovery restores the People note and retry succeeds without a Research artifact. |
| Hot presentation identity and retention | Original probe retains the current normalized claim, increments revision to 2, and admits a duplicate unchanged save. |
| Idea retrieval classification | Original probe returns the idea for the idea filter and no result for the knowledge filter. |
| Native configuration revocation | Original probe denies subsequent add/read and returns no retrieval results. |
| Concurrent native writers | Original probe acknowledges all four writes and recalls all four facts. |
| Schema 1 refusal | Original probe refuses access and leaves the schema version unchanged. |
| Native patch consistency | Top-level patch, bundled patch, and earlier reviewed patch snapshot are byte-identical. |

The full suite includes the five new host-context tests. They passed as part of discovery. I did not independently review `memory_context.py`, which is outside this closure scope.

## Evidence

- `raw/memory-tests.txt`: complete 61-test output.
- `raw/native-probes.jsonl`: complete results from the unchanged original eight-case script.
- `raw/followup-probes.jsonl`: complete results from the unchanged follow-up script.
- `raw/closure-probes.jsonl`: results for the three additional cases.
- `raw/probe_closure.py`: reproducible script with assertions for those three cases.
- `raw/commands.txt`: exact verification commands and their exit status.
- `raw/reviewed-hashes.json` and `raw/reviewed-*`: source snapshots and SHA-256 hashes identifying the inspected state.

All probes used `/home/outsider/.cache/lifeos-plugin-memory/sdk-env/bin/python` and disposable synthetic fixtures. Native operations used the source-only fixture at `/home/outsider/.cache/lifeos-plugin-memory/managed-source/LifeOS/install`. Reviewer probes built the actual native prompt without calling a model.

## Boundaries and remaining work

The code inspection covered the delta in `memory_access.py` and the added archive and reviewer regression tests. It did not repeat the full earlier foundation, recovery, service, or native-source reviews. Test passage is not evidence of an independent audit of every file reached by discovery.

The operating system remains the process trust boundary. A selected client name alone is not authentication against a process running as the same operating system user. This review does not change that statement.

Activation, provider integration, and proposal queuing and approval remain open work. Schema 2 remains development-only with deliberate refusal of schema 1. No migration or universal semantic paraphrase suppression is claimed.

No implementation code, commits, server configuration, live runtime, live memory, journal, or remote system was changed or accessed. Only review artifacts were written. No additional blocker was confirmed within this closure scope.
