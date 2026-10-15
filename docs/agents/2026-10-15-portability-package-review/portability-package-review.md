2026-10-15
Role: Independent complete portability package code reviewer
Question: Does the complete import, activation, reverse export, provider return, removal, and retained recovery package preserve current sources, owner authority, later edits, and recoverable state?
Model: gpt-6.1-sol, high reasoning effort

# Portability package review

Reviewed baseline: `8df5cf5b9e5558333c12ce0f2867551c357a42fe`.
Reviewed tip: `01d67f911ab41bca8e5eaf99d0f040b69af04dfb`.
Product checkpoint: `52db5dfd497ef3eed3e35e211b177026e247824c`.

**One measured P2 finding requires correction. The first working-tree correction closes two effects but leaves an earlier source-capture window open. The package is not CLEAR yet.**

## R1. P2: Return preparation can admit a later edit and publish an older result

Location: `lifeos_hook_bridge/memory_return.py`, `MemoryReturn.prepare`, initially lines 93-124 in `source/`.

Preparation checks the export sources, reads and transforms the Hermes configuration, and constructs the disabled ownership policy. It then captures the five live before-images. An edit between transformation and capture becomes the accepted before-image even though the output still uses the older input. The outer service transition accepts those before-images and publishes the stale output.

Two independent controls reproduce the issue through actual native fixtures and actual `MemoryTransition.prepare_return` and `apply` service operations:

1. Append an unrelated `synthetic_later_owner_setting: keep` setting when the actual `_configuration` transformation returns. Preparation reports ready. The normal return publishes the older configuration and loses that setting.
2. Add an unrelated account grant at the same boundary. Preparation accepts the later policy as its before-image. Return publishes the older selected policy and loses the new account grant.

These controls inspect the specific later setting and grant. They do not reject the legitimate provider and ownership changes that return must make. Both targeted assertions fail. `review-package-return-capture-targeted` retains the exact failure output.

### Initial correction and remaining window

The primary agent independently reproduces the two effects and adds product regressions. Its initial correction captures all five before-images first, transforms those captured inputs, checks the captured policy against the selected policy, and checks current files against those inputs before publishing the return review.

That correction preserves the two edits after transformation. It does not bind a newly captured built-in source to the earlier export source review. An edit immediately after `exporter._current()` returns, but before the five inputs are read, becomes a new accepted baseline.

A third independent control adds a new entry to `memories/MEMORY.md` at this boundary. Preparation still reports ready. Actual service orchestration applies the older export. The new entry disappears from active built-in memory. The targeted entry-preservation assertion fails. The copied before-image retains the bytes, but the normal return still publishes stale source contents. `review-package-return-source-capture` preserves this failure against the initial correction.

Required correction: Bind the captured inputs to both the transformation and the reviewed export source. A source revalidation after capture, together with the existing exact input recheck before review publication, can refuse this earlier edit. Preserve the later bytes and require a new current export review. Retain the exact owner, signature, writer, and per-target publication checks.

Exact independent probes are in `package_probes.py`:

- `ReturnCaptureControls.test_config_edit_after_transform_is_preserved`
- `ReturnCaptureControls.test_policy_edit_after_transform_is_preserved`
- `PreCaptureSourceControls.test_builtin_source_edit_before_input_capture_is_preserved`

All use synthetic files and real service fixtures under the shared fixture lock. Trace callbacks inject the actual later bytes at the named real function boundary. They do not replace source checks, service admission, publication, or recovery with mocks.

## Package audit and passing verification

The review inspects the exact baseline product diff and the current contract. It traces source upload and occurrence review through import publication, activation and local route grants, reverse export, current-state return, software removal admission and inventory, stock runtime construction and identity, retained source selection and authority, service draining, program publication, and standalone recovery authentication.

The review also reads the earlier transition, final removal, retained-source, coordinator, environment normalization, and runtime backup reports. It does not re-report their closed findings or treat their component clearances as installed acceptance.

The focused interaction run passes **121 Python controls** with clean diagnostics:

- Import and export validation, capacity, provenance, retirement, current targets, and idempotence.
- Actual authenticated HTTP owner sessions, unknown owner and foreign-origin refusal, fixed source identifiers, and no-store downloads.
- Complete removal publication, real process interruption, later built-in data retention, current and retained owner policy, and actual password authentication.
- Native SQLite barriers, exact retained source and typed lease selection, program publication and restoration, environment transformation, and executable/link identity checks.

A separate run passes **21 SDK component controls** against the actual bundles. These cover explicit per-item decisions, source provenance, owner refusal, local account and route disclosure, separate owner application, removal acknowledgement, and managed release UI behavior.

Commands and full outputs are preserved in `review-package-publication-boundaries.*`, `ui-command.json`, `ui.stdout`, and `ui.stderr`. These runs do not include the three failing boundary controls. They do not establish that R1 is fixed.

## Evidence integrity and source changes

`source-pin.json` records each changed product file against the exact reviewed Git tip. `source/` preserves those bytes. `product.patch` and `product-stat.txt` contain the exact main-baseline product comparison.

Only the primary agent's `memory_return.py` correction changes product bytes during this review. `source-stability-during-review.json` records its initial correction hash and confirms the other captured product files still match. `initial-correction-source/` and `return-correction-initial.patch` preserve the initial correction inspected here. The broad interaction run is repository component evidence, not exact archive qualification.

The first exploratory `review-package-return-capture` run compares complete before and after configuration bytes. That assertion is too broad because return legitimately changes provider and ownership fields. Its failures are retained as harness history and are not used to establish R1. The corrected targeted assertions prove loss of only the later unrelated values. Their two failures and the third source-entry failure are the finding evidence.

No product source is changed by the reviewer. No files are staged or committed. The primary agent owns all correction edits.

## Qualification limits

The tests use real synthetic files, native memory operations, SQLite, actual user services, actual process exits, actual local owner authentication, and fresh stock constructors where specified. SDK tests remain component fixtures.

Fresh constructor verification reports `model_turn_executed: false`. Some older host controls send requests to scripted local HTTP responses. Neither establishes a real private FlashNext model turn. The reviewer accesses no guest, personal source records, memory MCP records, or journal records.

Normal corrected removal, installed stock model behavior, reboot, authenticated retained-helper recovery and rollback, injected installed process kills, final archive qualification, and release promotion remain primary-agent gates. Their pending status is not reported as a code defect. The old operator-assisted environment repair is not counted as unaided recovery evidence.

The next review must repeat all three finding controls and the appropriate return and transition regressions against a committed final correction before the package receives code clearance.
