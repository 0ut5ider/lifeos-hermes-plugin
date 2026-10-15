# Portability primitive closure review

Date: 2026-10-15
Role: Independent focused closure reviewer
Question: Do the fixes resolve all three original P2 findings in the import, export, and provider-return primitives?
Model: gpt-6.1-sol, high reasoning effort

Result: All three original P2 findings are closed on the final inspected primitive code. The closure controls find no remaining defect in those fixes. This result does not qualify service orchestration, complete removal, the live daily installation, or a release.

## State and scope

Branch: `feature/memory-portability`.
Base commit: `8df5cf5b9e5558333c12ce0f2867551c357a42fe`.
The implementation is uncommitted. The primary agent changes worker orchestration, API integration, and UI integration independently. The review does not treat those unfinished workflows as defects by absence.

`inspected-hashes.json` records the initial closure state. `final-candidate-hashes.json` identifies the final candidate. The `reviewed/` and `final-reviewed/` directories preserve both code states. Product changes during this review add complete import-receipt provenance and importer-contract validation to export preflight. The final controls include both changes.

Final primitive identities:

- `memory_import.py`: `62886b8111ebd5dac2a3948e42320963e005a2df23e86bbadd778a5244963dd9`.
- `memory_import_sources.py`: `2d49943a9be8d4090c4bc1c3778e7635a48468821d0bb1280be0bb37f7110d3d`.
- `memory_export.py`: `bc235b56332c47189378764a4a872c5a84263acf19beb8b6a48160ef5d2906f0`.
- `memory_return.py`: `6aa1c3677e7d5ed0a4c7b3d38d76af34bf08815863aea2897306111e4b861d3d`.

The review changes only its own report, synthetic controls, and raw output files. It does not edit product code, commit, access personal data, read private source archives, or call memory or journal tools.

## Original findings and closure

### P2: Nested YAML aliases change unrelated settings

Status: Closed.

Fix: `memory_return.py:30-35` creates independent modified containers. Lines 59-70 detach enabled and disabled lists, the entries map, and each modified LifeOS entry.

The original nested-alias regression passes. Additional controls cover an aliased disabled list and entries map, both LifeOS plugin names, an unrelated plugin, and a merged individual LifeOS entry. The controls compare semantic values before and after the transformation. The unrelated values remain equal. Both LifeOS entries are disabled as intended.

No unresolved objection from the original alias finding remains.

### P2: Accepted export bundles fail their importer

Status: Closed within the declared bounded format.

Fixes:

1. The portable bundle limit is 16 MiB across staged upload, source collection, snapshot inspection, the browser upload, and the HTTP body envelope.
2. Original retained content uses the 1 MiB source bound. Native publication retains its separate smaller validation rules.
3. `memory_export.py:174-178` encodes the planned bundle, checks the total byte bound, and runs the actual portable parser before it writes the plan.
4. The raw-byte upload path preserves the original bundle bytes instead of requiring JSON reserialization.

The two original format mismatches pass their regressions. The larger variant creates a 1,232,037-byte portable download. Its noncanonical source serialization contains 1,223,116 bytes. Upload preserves those exact bytes. The review then snapshots, inspects, and plans all 21 items. All source origins, references, and fact text remain equal.

An additional refusal control creates 20 valid source receipts for one fact. The combined origin contains 23,245 bytes. The parser has a 16,384-byte origin bound. The export preflight refuses that plan before it writes `export-plan.json` or a portable bundle. This is a format-capacity refusal, not a successfully published bundle that later fails import.

The exploratory version of this control initially expected all provenance to fit. It returns a parser error before publication. That run remains saved as `review-primitives-closure-provenance-bound.*`. The final control asserts the expected refusal and passes. No product failure from that exploratory run remains unresolved.

No unresolved objection from the original successful-export/self-import mismatch remains. Large provenance can still prevent a complete export. The implementation reports a refusal and preserves the source; it does not truncate provenance or claim success.

### P2: Export overwrites a later output edit

Status: Closed for the measured multi-publication interleavings.

Fix: `memory_export.py:214-225` captures each output's current bytes and metadata, then rechecks that output immediately before publication. Lines 227-229 compare all final output bytes before publishing success.

The original regression now creates a private 0600 later `USER.md` edit after `MEMORY.md` publication. The exporter raises a conflict. It preserves the edit and does not create a success receipt.

The additional control edits the already-published first output after the portable bundle publication. Final verification raises a conflict. The edit remains intact, and no success receipt exists.

These controls use actual file writes and Python trace points between real publications. They do not replace product methods with mocks.

No unresolved objection from the original measured overwrite remains. The controls do not establish filesystem compare-and-swap semantics against an arbitrary noncooperating process that writes inside a single final-check/publication gap. The caller still needs the documented writer barrier for provider return.

## Provenance check

The final exporter gathers committed and unchanged source receipts for the native record. The independent control uploads a synthetic original source with a UTF-8 byte-order mark and CRLF newline. It imports one fact, then previews a reverse export.

The export includes the complete original receipt source under `origin.receipts`. The assertion compares the whole reference/source pair. The original source digest, source occurrence, source system label, private source identity, and unknown-author/date values remain present.

The larger portable-source control also compares every item origin and reference after upload, snapshot, and inspection. It confirms preservation of the original source bundle bytes.

## Verification and raw data

The final focused Python suite passes 62 tests. Exit status is 0. Elapsed time is 116.50 seconds. Its output and execution receipt are saved as `review-primitives-closure-final-baseline.*`.

The final closure controls run through the repository runner:

```text
python docs/verification/2026-10-15-memory-portability/run_tests.py review-primitives-closure-final-variants docs.agents.2026-10-15-portability-primitives-closure.closure_controls test_memory_return.MemoryReturnTests.test_shared_nested_yaml_values_do_not_change_unrelated_selections_or_plugins test_memory_export.MemoryExportTests.test_portable_round_trip_retains_large_original_hermes_occurrences test_memory_export.MemoryExportTests.test_later_edit_to_second_output_is_preserved_during_publication docs.verification.2026-10-15-memory-portability.primary_review_probes.ExportReview.test_accepted_bundle_total_fits_portable_upload
```

Result: 10 tests pass. Exit status is 0. Elapsed time is 23.12 seconds. These include the four original fix regressions and six additional controls.

The dashboard SDK component suite also passes 3 tests. It is a unit test suite, not browser acceptance. Its command, raw output, and scope are saved in `ui-tests.*`.

Earlier closure runs remain preserved:

- `review-primitives-closure-baseline.*`: 61 focused tests pass before the last provenance regression and preflight change.
- `review-primitives-closure-originals.*`: The four original fix regressions pass independently.
- `review-primitives-closure-variants.*`: The first five variant controls pass.
- `review-primitives-closure-provenance-bound.*`: The exploratory origin-capacity refusal, with its original control source in `exploratory_provenance_control.py`.

`closure-control-results.json` records the final measurements and synthetic before/after values. `closure_controls.py` contains the final reproducible controls.

## Remaining acceptance boundaries

The review closes the original primitive findings. The primary agent must still verify writer draining, service restart and recovery, session rebuilding, complete removal, actual browser behavior, disposable installations, and release compatibility. The review does not access `.211`, `.213`, `.252`, or `.253`, and it does not claim those gates pass.
