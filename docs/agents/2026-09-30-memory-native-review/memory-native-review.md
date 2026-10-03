Date: 2026-09-30
Role: Independent native delegation, curation, and retention reviewer
Question: Do the managed native writer and reviewer paths preserve permissions, references, retention decisions, and publication recovery before activation?
Model: GPT-6. The session does not expose a more specific deployed model identifier.

# Native memory integration review

The full 48-test memory suite passes, as do separate runs of four curation tests and eight native delegation tests. Eight independent probes confirm four defects and verify concurrent native additions, configuration revocation, and refusal of schema version 1. The four defects need resolution before the reviewed integration is ready for activation.

The source snapshots and hashes in `raw/` identify the reviewed versions. The primary agent held these scoped files stable during the review. The top-level and bundled native patches are byte-identical.

## 1. High: a restricted reviewer can admit unlabeled personal history

Locations: `memory_access.py`, `filter_history`; native `MemoryReviewer.buildReviewerUserPrompt` patch.

`filter_history()` excludes all history when there are no read grants. With any read grant, it checks only retained records allowed by that scope. It has no source-audience admission check for the supplied transcript exchanges. A project-only scope can therefore process personal history even though hot-memory loading correctly withholds principal and assistant records.

The `project_only_reviewer_input` probe stores a synthetic principal marker, reduces the native context to project-only read and write grants, and supplies a historical exchange quoting that private marker. The real native reviewer prompt contains the private marker in its conversation section. Its principal and assistant snapshots are empty, which confirms that the leak comes through history rather than hot-memory loading.

This probe establishes the prompt-admission gap. It does not claim that a model was invoked, nor that current participant-supplied text can always be distinguished from private historical text. The current history request has no per-source audience metadata, so the service lacks the evidence needed to make that distinction.

The primary agent confirms that the intended interim policy is conservative: scopes without all categories must exclude unlabeled historical exchanges. Apply that admission rule before any reviewer model sees the prompt. A future less restrictive policy needs trusted source-audience metadata, not text-based inference about who supplied the history.

## 2. High: native related-link updates invalidate existing archive references

Locations: `memory_access.py`, `native_add`, `_record`, and `_content`; native note append with related-link frontmatter merge.

Project references retain absolute character offsets. Native archive addition can both append a new fact and extend the note's `related` frontmatter. Extending that frontmatter shifts all existing bodies while their metadata offsets remain unchanged.

The `related_links_preserve_record_offsets` probe saves a research fact, then adds another fact to the same note with a valid `related` link. Both additions return committed receipts. Get on the first reference then raises `MemoryConflict`; ordinary recall also raises because it visits the broken active row.

The earlier fact has not changed. A permitted native metadata update has invalidated its reference. Preserve section identity or update every affected offset in the same governed publication transaction. Validation must verify earlier references after the complete native operation, including frontmatter changes.

The final probe uses the native supported relation type `related`. An exploratory run used the invalid value `related_to`, which native validation correctly rejected; it was replaced before the recorded final reproduction.

## 3. High: new archive types lose their native routing and type identity

Locations: `memory_access.py`, `native_add`, `_corpus`, `correct`, and `_publication_paths`.

The native integration now accepts knowledge people and companies plus ideas. Records retain the broad project category but not enough native type information for later operations. Correction still constructs a research knowledge item for every project record.

The `nonresearch_correction_targets_unjournaled_archive` probe saves a person note under `KNOWLEDGE/People`. Correction snapshots that People file in the rollback journal but writes the replacement to `KNOWLEDGE/Research` because the correction item hardcodes research. The child exits at `_record`, after native publication and before metadata publication.

Restart recovery restores the original record but leaves the new Research file because the journal never covered it. Retrying the same correction commits and appends a second copy there. The probe records two corrected-fact occurrences in the Research file and both archive paths after recovery.

The same loss of native type also affects retrieval. `native_idea_type_filter` saves an idea and receives a native result of type idea. Governed retrieval with `typeFilter: idea` returns no results; `typeFilter: knowledge` returns the idea labeled as knowledge.

Preserve native type and entity routing in record metadata or derive them reliably from the authoritative native envelope. Corrections must use the correct native destination, and the journal target set must cover the actual publication. The supplied retrieval corpus must preserve the native type expected by supported filters.

## 4. Medium: presentation-only curation creates a tombstone for a still-current claim

Locations: `memory_access.py`, `_claim_digest`, `_curate_hot`, `_blocked`, and `filter_history`.

Normalized retention fingerprints intentionally ignore the hot prefix, case, and trailing provenance label. Curation nevertheless marks every removed exact entry as superseded, even when the replacement has the same normalized claim fingerprint.

The `normalized_current_claim_is_not_a_tombstone` probe changes `RULE: original retained fact` to `PREFERENCE: Original retained fact ~inferred`. Curation commits, and recall returns the new active entry. A recent history quote of the same current fact is then excluded, and an explicit remember of the exact active entry is rejected as requiring reactivation.

The active replacement and superseded prior row share a normalized claim fingerprint. The retained row is therefore treated as a removed claim even though that claim remains current.

Distinguish changed presentation from a withdrawn claim. Preserve or transfer the active claim identity when only prefix, case, or provenance changes, and create a suppression fingerprint only when the normalized claim is no longer current. The primary agent confirms this is the intended correction.

## Verified behavior

- Four simultaneous actual native add calls all commit, and governed recall returns all four acknowledged facts.
- Native full-list curation after its own read works and preserves references for unchanged entries.
- An explicit write between a native read and a later full-list write causes the stale native update to reject.
- Invalid overlength native replacement is rejected without losing the original rule.
- A forgotten fact cannot be reintroduced through the tested prefix/case/provenance variation.
- Missing host context prevents private recall and native writes.
- Removing native read/write grants is observed by subsequent actual native calls: add rejects, read rejects, and retrieval returns an empty corpus.
- Managed LoadMemory excludes private hot entries without an approved context and includes them in the authorized fixture.
- The reviewer excludes old exchanges before the tested correction and excludes a recent exact normalized quote of a forgotten fact in the full-authority scope.
- Without a connector, native functions retain their original unmanaged behavior, as explicitly intended.
- Schema version 1 is refused. The test leaves its version at 1 and performs no migration.

These results establish the tested native boundaries. They do not imply that arbitrary paraphrases are recognized or that all historical sources have audience metadata.

## Explicit planned capability gap

The primary agent confirms that proposal queuing and approval remain open before activation. `native_add()` currently rejects proposal items, while native reviewer output can include proposals. This is recorded as a planned capability gap rather than an additional defect against a completed proposal implementation. Activation must wait for the promised proposal behavior and its evidence.

The deliberate coarse history cutoff can exclude unrelated older exchanges after a correction or forget decision. That tradeoff was explicitly supplied for review. This report does not count it as a defect and does not claim universal semantic forgetting.

## Test commands and results

Interpreter: `/home/outsider/.cache/lifeos-plugin-memory/sdk-env/bin/python`.

| Test run | Result |
| --- | --- |
| `test_memory_curation.py` | 4 tests pass in 4.220 seconds |
| `test_memory_delegation.py` | 8 tests pass in 6.834 seconds |
| Full `test_memory_*.py` suite | 48 tests pass in 29.637 seconds |
| Independent probe script | 8 cases complete; findings and successful boundary checks are preserved |

All tests ran against the managed-source native fixture with synthetic data. No tests were skipped. The probe script records actual outcomes; its defect reproductions are not passing regression tests.

## Scope, boundaries, and artifacts

Reviewed implementation: curation, normalized retention and history filtering in `memory_access.py`; `memory_native.ts`; `MemoryService.native`; `memory_rpc.py`; the managed native patch; targeted tests and public native source needed to assess archive and reviewer behavior.

Native host context is supplied through the trusted environment and resolved against server-owned configuration. The internal bypass and local connector remain inside the same-UID operating-system trust boundary. This review does not claim isolation from a process that can change those files or environment settings and directly access the memory store.

All reads and writes used temporary synthetic roots or public native source. No production memory, production logs, live runtime, remote host, deployed configuration, memory service, or journal service was accessed. No implementation edits or commits were made by this reviewer. Provider and enrollment work running independently in the same checkout was outside this review.

Artifacts:

- `raw/memory-tests.txt`, `raw/curation-tests.txt`, and `raw/delegation-tests.txt`: complete test output.
- `raw/probe_native.py` and `raw/native-probes.jsonl`: all eight independent reproductions and boundary checks.
- `raw/reviewed-*`, `raw/native-*`, and `raw/reviewed-hashes.json`: reviewed plugin and native sources with hashes.
- `raw/commands.txt`: exact commands and diagnostic notes.

The restricted-history admission and archive transaction/reference issues deserve review before activation. Normalized claim identity must also distinguish a presentation update from removal. Proposal behavior remains a separate declared acceptance gate.
