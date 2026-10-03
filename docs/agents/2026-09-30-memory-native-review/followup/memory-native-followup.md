# Native memory integration follow-up review

Date: 2026-09-30  
Role: Independent bounded code and synthetic integration reviewer  
Question: Do the four native integration fixes and conservative private entity guard preserve references, recovery, retention, and audience permissions?  
Model: GPT-6. The exact model variant is not exposed in this agent context.

## Outcome

The four original defects are corrected in their reproduced cases. All 54 memory tests pass. The eight unchanged original probes also confirm the expected corrections and preserve the earlier concurrency, revocation, and schema refusal behavior.

Two adjacent defects remain in the changed permission behavior. Both are reproduced with disposable synthetic fixtures and real native tools. The first admits history from an unauthorized project into the actual reviewer prompt. The second can acknowledge a correction while leaving the caller without an accessible current fact.

## Findings

### 1. High: unlabeled reviewer history still bypasses project restrictions

Location: `lifeos_hook_bridge/memory_access.py:537`, especially the admission check at line 540.

The new admission check requires every native category in `scope.read`. It does not require access to every project. A caller with principal, assistant, and project permissions but `projects=('lab',)` can still pass unlabeled history from project `other` to the reviewer.

The probe saved a synthetic fact under project `other`, configured the native destination for project `lab`, and passed a historical exchange containing the other-project marker through the real native `review_prompt` path. Direct recall with the same category and project grants returned no records. The resulting reviewer prompt included the exact other-project marker in its conversation section.

This is the project form of the original source admission defect. There is no per-source project label with which to prove that an exchange is authorized. Until such labels exist, the conservative gate also needs unrestricted project access. Test the actual reviewer prompt with all categories but a restricted project list.

Evidence: `raw/followup-probes.jsonl`, case `all_categories_but_restricted_project_history`. No model was invoked.

### 2. High: duplicate matching merges public facts into inaccessible private entity references

Locations: `lifeos_hook_bridge/memory_access.py:481` and `lifeos_hook_bridge/memory_access.py:616`.

The new People and Companies guard distinguishes private entity records from other project records. The duplicate searches in `remember()` and `correct()` still match only the content digest, category, project, and active status. They do not preserve this permission distinction.

The probe created a People record as the owner. A project-only caller then saved the same content as an ordinary project fact. The save returned `status='unchanged'` with the private People reference. `get()` rejected that reference and scoped recall returned no fact.

The correction variant has a stronger effect. The project-only caller first created an accessible Research fact, then corrected it to content matching the private People record. The correction returned `status='committed'` with the People reference and superseded the accessible Research record. A read of the old reference returned `conflict`; a read of the returned replacement reference was rejected for lack of permission.

Duplicate matching must preserve the record's audience and native visibility class. At minimum, an inaccessible private record cannot satisfy a public save or correction. Matching only rows the current caller can access is insufficient as a general visibility invariant: a fully authorized owner can access both classes, while later project-only callers cannot. Preserve the intended visibility of the destination when selecting a reusable record.

The direct native entity-write guard itself behaved correctly: a project-only native People add was rejected before publication. The defect is the separate duplicate reuse path.

Evidence: `raw/followup-probes.jsonl`, case `project_save_collides_with_private_entity`.

## Original fixes verified

| Original issue | Current evidence |
| --- | --- |
| Related-link frontmatter edits invalidate older references | The unchanged probe appends a valid related link. Both facts remain readable and recall returns both. `_archive_write()` validates existing sections, verifies the unchanged body prefix, shifts active positions by the frontmatter delta, and validates the shifted sections. |
| Nonresearch correction writes to an unjournaled Research path | The actual child process exits with code 73 after native publication and before `_record()`. Recovery restores the People note, leaves no Research note, and the same request retries successfully. The new regression also checks exactly one corrected occurrence. |
| Ideas lose native retrieval classification | The idea filter returns the saved idea; the knowledge filter returns no results. |
| Hot presentation changes create a false tombstone | The replacement keeps the reference ID and increments its revision to 2. The current normalized claim is admitted to history, and an identical subsequent save is unchanged. |
| Project-only reviewer processes personal history | The actual reviewer prompt now contains zero exchanges for the original project-only case. Finding 1 identifies the remaining project dimension. |
| Private entity guard | The new read regression passes, and the independent probe confirms direct project-only entity writes are denied. Finding 2 identifies duplicate reuse outside that guard. |

## Verification

Interpreter: `/home/outsider/.cache/lifeos-plugin-memory/sdk-env/bin/python`.

Native source fixture: `/home/outsider/.cache/lifeos-plugin-memory/managed-source/LifeOS/install`. It supplied public native code only. Each test or probe created disposable synthetic configuration and data.

- Full `test_memory_*.py` discovery: 54 tests passed in 34.706 seconds, process exit 0, no skips reported.
- Original probe script rerun unchanged: eight cases completed, process exit 0. Results were inspected against the prior findings.
- Follow-up probe script: two cases completed, process exit 0. The second case includes both save and correction variants.
- Original real native concurrency probe: four separate native call sequences all acknowledged their writes; recall returned all four facts.
- Original configuration revocation probe: subsequent native add and read were denied, and retrieval returned an empty corpus.
- Original schema probe: schema version 1 remained version 1 and native access refused it.
- Top-level and bundled native patches are byte-identical to each other and to the previous review snapshot.

`raw/memory-tests.txt` contains the complete test output. `raw/native-probes.jsonl` and `raw/followup-probes.jsonl` contain the full probe results. `raw/probe_followup.py` contains the new reproducible probes. The unchanged original script remains at `../raw/probe_native.py` relative to this follow-up directory. `raw/commands.txt` records the exact verification commands. Source snapshots and SHA-256 hashes identify the reviewed state.

## Scope and limits

This review inspected the delta in `memory_access.py`, the new archive tests, and the restricted reviewer test. It reran the full memory test gate and earlier native probes. It did not repeat the entire foundation, service, or native-source audit. The native patch did not change.

The process boundary still relies on operating system isolation. A configured client name alone does not authenticate an adversarial process running as the same operating system user. This review makes no stronger claim.

Proposal queuing and approval remain a planned capability gap before activation. Schema 2 remains development-only, and schema 1 refusal is deliberate. No migration or universal semantic paraphrase suppression is claimed.

No implementation code, server configuration, live runtime, live memory, journal, or remote system was changed or accessed. Only review artifacts were written. The two findings above need correction and verification before this permission behavior can be considered closed.
