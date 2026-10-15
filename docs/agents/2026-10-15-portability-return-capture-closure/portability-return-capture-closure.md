2026-10-15
Role: Independent portability return-capture closure reviewer
Question: Does committed b35cf86e close all three measured return-preparation lost-edit effects while preserving source, owner, service, and recovery bindings?
Model: gpt-6.1-sol, high reasoning effort

# Portability return-capture closure

**CLEAR within the tested code-review boundary. R1 is closed. No new actionable finding is established.**

Reviewed commit: `b35cf86ef032ab81ac4306d48951b94615aca5a4`.
Prior full-package review tip: `01d67f911ab41bca8e5eaf99d0f040b69af04dfb`.
Full-package baseline: `8df5cf5b9e5558333c12ce0f2867551c357a42fe`.

The previous complete package review establishes one P2 finding, R1. It proves lost later configuration settings and owner grants, plus a built-in source entry written before input capture. The original report and red data remain intact in `../2026-10-15-portability-package-review/`. This closure supersedes its open disposition for R1 only. It does not convert component evidence into installed acceptance.

## Correction review

`MemoryReturn.prepare` captures all five target files before it derives output or retains before-images. It revalidates the complete reviewed export source after capture through the existing `MemoryExport._current` method. This includes the current owner-policy digest, Hermes settings and source identities, source origin, and native target signature. It parses the captured policy and requires equality with the admitted policy. It derives configuration output from captured bytes and retains those same captured bytes and modes in the journal. Immediately before publishing the ready plan, it requires all five live files to equal the captured inputs.

The second reviewed-source validation closes the remaining pre-capture source window. The final equality guard closes edits after capture, including edits to the prompt and policy, which are not ordinary built-in memory source entries. An edit made after review publication still encounters the existing transition and return checks before application. This correction does not alter the journal format, owner admission, writer barriers, native target validation, retained source data, or rollback rules.

I inspect the exact product diff and the four added product regressions. Source hashes are in `source-pin.json`. `source/` preserves those exact source bytes and the unchanged original independent probes. `package-source-stability.json` verifies all 43 product files captured by the prior full-package review against this commit. Only `lifeos_hook_bridge/memory_return.py` changes between those reviewed product snapshots. The new test additions are separately pinned. Current source hashes still match after both test runs.

## Reproduced closure controls

All three unchanged independent controls now pass:

1. The unrelated setting `synthetic_later_owner_setting: keep` survives a write immediately after configuration transformation.
2. The unrelated grant `synthetic:later-owner-account: owner` survives a write at the same boundary.
3. A synthetic built-in entry written after the first reviewed-source check and before input capture survives.

Each control now observes preparation refusal before a ready plan can be applied. The controls retain their actual native filesystem fixture and actual profile-service fixture. Their original red executions establish loss through the actual service transition. The successful closure does not need to drain the services because it refuses the stale preparation first.

Four additional independent controls also pass:

1. A previously missing `memories/USER.md` created immediately before capture remains intact, and preparation refuses.
2. A later `SOUL.md` prompt written after the second reviewed-source check remains intact, and preparation refuses.
3. Revocation of the current dashboard owner after the second source check remains intact, and preparation refuses.
4. A mode-only change to `config.yaml` after the second source check remains intact, and preparation refuses.

These four controls use real synthetic files and actual preparation. The trace callbacks inject writes at real function-return boundaries. They do not replace product functions. The controls assert the retained edit and absence of a published ready return directory. Their source is `adjacent_controls.py`.

## Regression evidence

The frozen runner reports **51 tests PASS** in 125.036 seconds, with process and strict exit status 0 and no unhandled diagnostics:

- `test_memory_return`: current settings and YAML alias retention, required writer barrier, later-edit refusal, exact rollback, and actual child-process exit and resume after first publication.
- `test_memory_transition`: actual user-service drain, retained Pulse disablement, recovery after interrupted publication, safe retry, and later built-in edit protection.
- The three original independent R1 controls.
- `test_memory_import` and `test_memory_export`: source and owner binding, actual native data publication, process-exit recovery, per-item review, capacity, provenance, retirement protection, and portable round trips.
- `test_memory_removal_workflow`: retained authority, other-owner refusal, separate owner application, and bounded removal selection.

The adjacent run reports **4 tests PASS** in 9.586 seconds. Its process and strict exit status are 0, with no unhandled diagnostics. Both runs have empty standard output. Expected interruption and error behavior is captured and asserted by the tests. Actual service tests use the shared `service_manager_fixture` flock and fixture-owned units with cleanup.

Exact executable arguments are in `command.json` and `adjacent-command.json`. Reproduce with the respective `run_closure.py` and `run_adjacent.py` supervisors, or use their recorded frozen-runner arguments with new unique labels. Each supervisor copies the raw runner receipt, standard output, standard error, and completion marker into this folder. The labels used here are `review-return-capture-closure` and `review-return-capture-adjacent`.

The initial pinning command uses an incorrect fixture filename and stops before test launch. It is corrected to the actual fixture in `tests/test_profile_services.py`. This is a reviewer setup correction, not a product failure. No failed product test result is suppressed.

## Limits and remaining gates

This is local code-review closure with synthetic data. The return and transition suites contain real filesystem, native data, service-manager, and process-exit operations. The adjacent edit controls are preparation checks. Neither is a fresh installed browser workflow or a real private-model inference.

The earlier 121 Python and 21 SDK full-package interaction passes remain separate historical evidence. They are not added to the 55 closure controls or presented as a rerun at this commit. No SDK code changes in this correction.

Installed corrected return and removal, native and stock model behavior, guest reboot, retained-helper authenticated recovery and rollback, injected installed process termination, final package qualification, and release promotion remain primary-agent gates. A constructor result is not a model turn. Earlier operator-assisted recovery is not unaided recovery evidence.

No product source, Git state, remote guest, personal record, memory MCP record, or journal record is changed by this reviewer. Reviewer-owned local synthetic services are created and cleaned by the established fixtures. This closure finds no remaining code defect in R1 or its measured adjacent boundaries. It does not qualify the complete installed release.
