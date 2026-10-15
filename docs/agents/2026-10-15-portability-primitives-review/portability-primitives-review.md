# Portability primitive review

Date: 2026-10-15
Role: Independent focused code reviewer
Question: Do the current memory import, export, and provider-return primitives preserve authority, data, complete accounting, and their stated results?
Model: gpt-6.1-sol, high reasoning effort

Result: Three actionable P2 findings. The existing focused tests pass, but four additional synthetic controls reproduce defects. Do not treat this review as release qualification.

## Inspected state

Branch: `feature/memory-portability`.
Base commit: `8df5cf5b9e5558333c12ce0f2867551c357a42fe`.
The implementation is uncommitted. `inspected-hashes.json` records the initial file identities. `completion-hashes.json` records the final inspected identities. Only the dashboard JavaScript changed during the review. The primary agent owns that concurrent change.

Relevant product hashes:

- `memory_import.py`: `341969f9bd3edcb2b1ed22fb6a8feb7952edac1b4012540ff0a01bb33724d293`.
- `memory_import_sources.py`: `f39719fc79fb875f4c586d5370ce98be63247b4b38f0bd083d65c272bf7a75a0`.
- `memory_export.py`: `8df6199b855a15d9dcfbcadb512138682c3a5a8310aabaa74be42a21be1ad5f3`.
- `memory_return.py`: `4cfca761778859ef7939aada68b35891e4ff747336301c610f99c7057942d0e8`.

The `reviewed/` directory preserves the inspected product and test files. The review does not change product files, commit, access private source archives, read personal data, or call memory or journal tools. All fixtures contain synthetic data.

The reviewed scope excludes unfinished return service orchestration, complete removal, disposable guest acceptance, browser acceptance, and release qualification. Their absence is not a finding.

## Findings

### P2: Nested YAML aliases change unrelated settings during provider return

Location: `lifeos_hook_bridge/memory_return.py:50-59`, particularly the mutations at lines 55, 56, and 59.

The configuration validator rejects anchored or merged top-level mappings. It does not reject aliases in the plugin selection lists or individual plugin entries. Ruamel preserves alias identity. The list slice and entry mutation therefore change every alias to those objects.

The reproduction supplies this valid configuration:

```yaml
other_selection: &shared [lifeos, other]
other_entry: &entry {enabled: true, custom: keep}
plugins:
  enabled: *shared
  entries:
    lifeos: *entry
    other: *entry
memory:
  provider: lifeos-hook-bridge
```

`MemoryReturn._configuration()` removes `lifeos` from `other_selection`. It also sets both `other_entry.enabled` and `plugins.entries.other.enabled` to false. The unrelated plugin is disabled. The primitive returns a configuration instead of refusing it.

Reproduction: `review_probes.ReturnConfigurationReview.test_aliases_do_not_change_unrelated_settings`.

Suggested fix: Refuse anchored, aliased, or merged mutable objects on every modified configuration path. Alternatively, detach each modified branch without changing its aliases. A general deep copy can preserve alias sharing, so it is insufficient by itself. Verify that unrelated configuration values remain equal. Add tests for aliased enabled and disabled lists, the entries mapping, and individual LifeOS entries.

### P2: Accepted export bundles cannot pass the corresponding portable importer

Locations:

- `lifeos_hook_bridge/memory_export.py:57-58`, accepted source content totals.
- `lifeos_hook_bridge/memory_export.py:191-194`, bundle construction.
- `lifeos_hook_bridge/memory_import_sources.py:67`, individual content limit.
- `lifeos_hook_bridge/memory_import_sources.py:94`, encoded bundle limit.

The exporter accepts up to 2 MiB of fact bodies. The serialized bundle repeats content in the source review and each planned item. The importer accepts only 1 MiB of the complete encoded bundle. It also rejects a retained source occurrence longer than 65,536 characters, although the exporter accepts and retains such an original Hermes occurrence.

Two independent controls reproduce the mismatch:

1. Twenty original Hermes entries have a maximum length of 29,991 characters. Their combined item content is 599,838 characters. Export and download both succeed. The exact downloaded bundle contains 1,231,507 bytes. `upload_bundle()` refuses it with `The portable source exceeds its import byte limit`.
2. One retained original Hermes occurrence contains 70,027 bytes. Export and download both succeed. The exact bundle contains 144,214 bytes. `upload_bundle()` refuses it with `A portable source fact has invalid content or provenance`.

The second case does not exceed the total upload limit. Increasing only that total limit does not fix the individual retained-source mismatch. Both cases prevent the owner from restoring a bundle that this implementation creates successfully.

Reproductions:

- `review_probes.ExportReview.test_accepted_bundle_total_fits_portable_upload`.
- `review_probes.ExportReview.test_retained_export_can_be_imported_as_a_portable_source`.

Suggested fix: Define one bounded portable format contract for aggregate encoded bytes, item count, individual source size, and metadata size. Make export preflight, download, upload, source snapshot inspection, HTTP request limits, and the browser file limit use that contract. Original retained text can require a larger review bound than native publication text. Keep the existing native write validation. Confirm that every successfully published bundle can pass upload and complete item review, including retained overflow.

### P2: Export publication overwrites a later edit to an output artifact

Location: `lifeos_hook_bridge/memory_export.py:196-202`.

The exporter checks all output paths once. It then publishes each path after only rechecking the source. A later edit to an output that has not yet been published is overwritten.

The reproduction uses actual file writes and a Python trace hook. Immediately after `hermes/MEMORY.md` publication returns, it creates `hermes/USER.md` with `Synthetic later owner edit.`. The exporter then replaces that file with empty bytes. `apply()` returns `state: exported`.

The trace hook does not replace or mock a product method. It creates a reproducible scheduling point between real publications. The current test suite does not cover this interleaving.

Reproduction: `review_probes.ExportReview.test_edit_to_later_output_is_preserved_during_export`.

Suggested fix: Validate each destination against its expected current identity immediately before its publication. Refuse and retain changed outputs. Use a shared artifact lease or writer barrier if the workflow requires stronger protection against concurrent writers. Validate all final artifact bytes before publishing a success receipt. Add process interruption and later-output-edit controls for both Hermes files and the portable bundle.

## Verification

The required repository runner uses the existing qualified native LifeOS fixture and frozen Hermes test environment:

```text
python docs/verification/2026-10-15-memory-portability/run_tests.py review-primitives-baseline test_memory_import test_memory_export test_memory_return test_memory_import_dashboard test_memory_export_dashboard
```

Result: 58 tests pass. Exit status is 0. Elapsed time is 108.56 seconds. These tests exercise actual synthetic native memory and owner HTTP requests. They do not verify the live daily installation.

```text
node --test tests/test_memory_portability_ui.cjs
```

Result: 3 component unit tests pass. These tests use an SDK test implementation. They are not browser or end-to-end acceptance.

```text
python docs/verification/2026-10-15-memory-portability/run_tests.py review-primitives-probes-full docs.agents.2026-10-15-portability-primitives-review.review_probes
```

Result: 4 added controls fail as expected: 2 assertion failures and 2 rejected self-round-trip errors. The control results establish the three findings above. They do not indicate failures in the 58 existing tests.

Raw data:

- `probe-results.json`: The final full-run measurements and synthetic YAML before/after values.
- `bundle-total-results.json`: The separate aggregate-size measurement.
- `review-primitives-baseline.{stdout,stderr,json,done}`: Existing focused suite output and execution receipt.
- `review-primitives-probes-full.{stdout,stderr,json,done}`: Full reproduction output and execution receipt.
- `review-primitives-probes.*` and `review-primitives-bundle-size.*`: Initial bounded reproductions.
- `ui-tests.{stdout,stderr,json}`: Component unit test output and scope.
- `review_probes.py`: Reproducible synthetic controls.

## Limits

No real source data was imported or exported. No live services, stores, scheduler jobs, release assets, guest configuration, or personal files were changed. The review does not establish a complete product or release acceptance result. The primary agent must verify fixes against the measured controls and complete the remaining workflow gates.
