# Native source adoption review

Date: 2026-09-30
Role: Independent code reviewer
Question: Are preview/adoption consistency, exact source identities, source permissions, retained claims, and learning correction rollback correct in the bounded native-source adoption unit?
Model: GPT-6. The exact model variant is not exposed in this agent context.

## Conclusion

Three material findings remain in the reviewed snapshot. All 13 supplied adoption tests passed, but four additional real fixture cases exposed the findings below. This unit is not closed. Each reproduction uses the prepared source and disposable synthetic records. No implementation files were edited, no commits were made, and no live systems or memory/journal tools were accessed.

The primary agent received all findings before this report. Any subsequent fixes require separate verification against a new source snapshot.

## Finding 1: Adoption commits source references that ordinary recall cannot read

Severity: High for availability and reference integrity.

memory_adoption.py locates a discovered learning body using text.find(body), starting at the beginning of the entire file. If a single-line body also occurs in frontmatter, this chooses the frontmatter occurrence. In a real fixture with title and body both equal to Synthetic repeated title marker, adoption returned committed with facts_adopted=1. The next ordinary recall raised MemoryConflict: The referenced fact changed outside its recorded revision.

A second fixture containing a learning body followed by three trailing spaces produced the same committed-then-unreadable outcome. Adoption strips the body, while memory_access._content requires the remainder of the native section to match exactly after removing only newline characters. The trailing spaces make that check fail without any external edit.

These cases demonstrate disagreement between discovery, candidate construction, and the authoritative reader. Because _corpus reads allowed active records before ranking, one such adopted row can fail ordinary recall for the scope, rather than merely omit the malformed note.

Reproduction: raw/probe_adoption.py cases learning-title-equals-body and learning-trailing-space. Full receipts and exceptions are in raw/probe-results.jsonl. Source files remain unchanged after adoption.

Recommended correction: derive body offsets from the actual frontmatter boundary and establish one section representation shared by adoption and the authoritative reader. Validate every candidate through equivalent read checks before committing its reference. Decide explicitly whether trailing whitespace is part of the identity or ignored consistently.

## Finding 2: Preview signature does not bind timestamp-dependent eligibility

Severity: Medium for preview authorization and consistency.

Learning eligibility uses stat().st_mtime to exclude sources that predate retained corrections or forgetting. The preview signature includes file content digests and database rows, but neither the source mtime nor the resulting candidate/exclusion set.

The real fixture created a learning note with an old mtime, then forgot an unrelated fact. Preview correctly returned zero candidates and one exclusion because the source predates the retained change. The probe changed only the learning file's mtime. Adoption using the original signature returned committed with facts_adopted=1 and exposed that previously excluded note in recall.

The approved preview showed no adoptable record, yet the unchanged token authorized one. No file content or database record changed between preview and adoption.

Reproduction: raw/probe_adoption.py case mtime-preview. Output records preview_count=0, the original exclusion, and the receipt committing one fact.

Recommended correction: include every eligibility input in the signature, or bind a deterministic canonical candidate/exclusion snapshot in addition to the source digests. A timestamp change that alters eligibility must require a fresh preview.

## Finding 3: Hot-memory adoption can restore a wrapped exact forgotten quote

Severity: High for retained claim exclusion.

The adoption add helper checks _blocked against the entire normalized candidate. It runs the retained substring/history filter only for category project. Principal and assistant hot-memory candidates therefore bypass quote filtering.

The fixture saved and forgot RULE: Synthetic retired routing port 8123. It then used the real native writer to add RULE: Historical note says Synthetic retired routing port 8123 in retained history. Preview offered the hot entry without an exclusion, adoption committed it, and ordinary recall returned the retired claim inside the new rule.

This is an exact normalized quote, not a semantic paraphrase. The existing archive test covers this shape for project sources, but the equivalent hot source is permitted.

Reproduction: raw/probe_adoption.py case hot-wrapped-forgotten. The output includes the adopted and recalled wrapped quote.

Recommended correction: apply the normalized retained quote guard across all adopted source categories. Keep timestamp handling specific to sources with meaningful historical timestamps if needed. The review does not request a universal semantic paraphrase guarantee.

## Passed checks and inspected behavior

All 13 adoption tests passed in 13.660 seconds against the requested prepared native source:

- Native facts retain their original files and use native:unattributed provenance.
- An identical adoption request returns the same receipt.
- Unassigned native project records remain hidden from restricted project readers; an explicit project assignment enables the intended project grant.
- Changed source text invalidates a preview.
- Exact previously forgotten native sections are not reactivated.
- Native pending proposals can be adopted, reviewed, and manually approved.
- Learning records are marked historical in recall and native context.
- Restricted readers cannot preview or adopt owner sources.
- Private markup and malformed hot markers are excluded.
- Unbounded discovery includes all 501 learning files while the unchanged default native path remains limited to 500.
- Distinct native appended sections receive distinct references and one can be corrected without losing its sibling.
- Wrapped forgotten quotes are excluded from project archive adoption.
- A real child process interrupted during learning-to-Research correction recovers the original state and removes the uncommitted new destination; retry succeeds.

The source changes preserve the native discovery default limit and make null explicitly request unbounded learning discovery. Top-level and bundled patches are byte-identical. The adoption transaction inserts metadata and references without rewriting the native source files. The correction target inventory now journals both the original learning path and the routed Research destination.

## Scope and evidence

Reviewed files:

- lifeos_hook_bridge/memory_adoption.py
- Current changes in lifeos_hook_bridge/memory_access.py
- Current changes in lifeos_hook_bridge/memory_native.ts
- tests/test_memory_adoption.py
- The discoverAllItems optional-limit changes in both LifeOS memory patches

The actual native fixture was /home/outsider/.cache/lifeos-plugin-memory/source-gate-20260930-adoption/lifeos/LifeOS/install. The test interpreter was /home/outsider/.cache/lifeos-plugin-memory/memory-plugin-test-env/bin/python.

raw/commands.txt contains exact test and probe commands. raw/tests.txt contains the complete successful suite output. raw/probe_adoption.py contains all four independent fixture cases; raw/probe-results.jsonl contains their receipts, exclusions, recall results, and exceptions. Initial snapshots, initial/final hashes, the reviewed diff, native retriever snapshot/hash, and patch equality result are saved in raw/.

## Limits

This was a bounded review of source adoption and directly affected native reference operations. It did not review new API/UI integration, fresh activation, all historical source formats, host admission, deployment, or backup lifecycle. Source changes outside this scope were not tested. Existing passing cases do not close the three confirmed gaps above.
