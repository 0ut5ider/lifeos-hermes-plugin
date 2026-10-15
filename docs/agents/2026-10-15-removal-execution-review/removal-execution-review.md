# Removal executable closure review

Date: 2026-10-15

Role: Independent read-only safety reviewer.

Question: Do the stock runtime and consumer fixes close the previous findings, and do adjacent executable inputs remain bound to the removal review?

Model: gpt-6.1-sol, high reasoning effort.

Reviewed commit: `a18c27d82be66b959d6c7732ffead816bd8eb86b` on `feature/memory-portability`.

Disposition: Both original workflow findings close under adapted real controls. The current suite passes 18 tests. Two adjacent P2 findings remain, reproduced twice with actual Python execution and an actual user service.

This review does not certify the complete installed preparer, browser workflow, worker, reboot, or a model turn. Those acceptance activities remain primary-agent work. The second-activation lifecycle question is also outside this bounded closure round.

## Findings

### 1. P2: Excluded bytecode remains executable input

Location: `optional/lifeos_release_manager/removal_runtime.py:27`, through the common `release_programs.fingerprint` bytecode exclusions.

The runtime identity deliberately ignores `__pycache__` and `.pyc` files. Python still reads valid bytecode from those paths. Disabling bytecode writes does not disable bytecode reads.

The new control uses the actual runtime fixture contract, including `stock_runtime_execution`. It creates a synthetic dependency module and records its source and execution identities. It then adds a valid timestamp bytecode cache containing different code. The cache header matches the unchanged source file's timestamp and size.

The runtime review still admits the program. A fresh actual isolated Python child imports the dependency and executes the changed cache value. The source file remains unchanged.

Safe receipt:

```json
{
  "changed_bytecode_admitted": true,
  "executed_value": "executed-unreviewed-cache",
  "source_unchanged": true
}
```

Probe: `execution_probes.ExecutedBytecodeReview.test_changed_bytecode_cannot_change_the_admitted_program`.

Evidence: `executed-bytecode.json` and the two adjacent-test runner outputs.

This is a dependency-import component proof. It does not claim to execute a complete removal or inject code into the installed sealed fixture. All cache files belong to the synthetic private runtime.

Required correction: Bind bytecode that the selected interpreter can execute, or ensure the selected commands and verification children cannot consume unreviewed caches. Preserve the intended tolerance for non-executable lock state without treating executable Python cache contents as equivalent to that state. A write-only bytecode switch is insufficient.

### 2. P2: An inactive basename Bun consumer still escapes service admission

Location: `optional/lifeos_release_manager/removal_consumers.py:68` and line 103, where cached execution metadata and definition bytes receive absolute-token checks.

The scanner now finds runtime-linked services, but it still requires an absolute selected executable or program token. A service can select the same Bun executable through its normal PATH environment.

The measured service uses `ExecStart=/usr/bin/env bun` and an explicit PATH whose first directory contains the selected account Bun command. Its synthetic script records `process.execPath`. The test starts the actual oneshot service, verifies that the recorded executable is the selected private Bun, and waits until the service is inactive with a successful result.

The subsequent consumer scan admits the service. There is no current Bun process for the process scan to catch. Removal would leave this unrelated service installed while deleting the executable that its next start selects.

Safe receipt:

```json
{
  "inactive": true,
  "selected_bun_executed": true,
  "foreign_consumer_admitted": true
}
```

Probe: `execution_probes.BasenameServiceReview.test_inactive_basename_bun_service_cannot_lose_selected_executable`.

Evidence: `basename-service.json` and the adjacent-test runner outputs.

The test uses the existing `service_manager_fixture` lock and a unique actual user unit. Cleanup stops that unit, removes its runtime link, and reloads the manager. It preserves no service command text or unrelated metadata in the safe receipt.

Required correction: Resolve supported basename execution and PATH forms, or refuse these unresolved consumer forms before removal. The existing conservative bare-Bun hook policy provides a bounded option for the first supported layout. Preserve the foreign service and its executable on refusal.

## Previous findings and their closure

The previous report at `3b01911f` found an unbound stock launcher and an inactive runtime-linked foreign service. `workflow_probes_original.py` preserves its original tests unchanged.

`execution_closure.py` adapts the stock probe to the new explicit identity contract. It copies the complete actual constructed 2.2 GiB stock runtime, rather than supplying only source and manifest files. It rewrites only contained absolute symlinks to refer to that private copy. It records `identity(root)` as `stock_runtime_execution` and confirms `_stock` accepts the unchanged copy before making the original launcher edit.

The changed launcher is now refused with the exact runtime-review rejection. Source and manifest identities still match, so this control demonstrates the new executable-identity check. It is not a missing-field rejection.

The original loaded inactive runtime-linked foreign service is also refused. The control verifies loaded, inactive, and linked-runtime metadata before calling the scanner. It uses the shared fixture lock and removes its unique unit afterward.

The earlier preparation findings remain closed under the prior review. This round does not undo their explicit before-image binding or the executable-path and home-expansion fixes.

## Current implementation assessment

The execution identity adds exact command, interpreter, dependency, package-manager bootstrap, feature, manifest, and runtime metadata. It checks that internal links resolve within the fixed runtime. The source fingerprint remains a separate review field. `_stock` checks the execution identity before dispatch and application and around the fresh constructor.

The supplied controls refuse later edits to all three launchers, a dependency source file, the pinned interpreter, the package-manager entry point, and feature metadata. They refuse an interpreter link that leaves the runtime. They retain the intended non-executable venv lock tolerance. Finding 1 concerns actual executable cache contents that the identity excludes.

The consumer inventory now reads effective manager unit directories, loaded fragment and override paths, and cached execution metadata. It checks trusted file type, ownership, mode, size, and stable read identity. It detects the original runtime-link case even when the service is inactive. Finding 2 concerns supported executable resolution after the unit is found, rather than failure to inventory the unit.

Current manager controls continue to reject another owner and another workflow, retain owner grants after active configuration removal, and keep preparation separate from application. Actual service publication controls retain later built-in memory and recover after real process exit. The fresh actual stock constructor control passes without a model turn.

No new measured owner-binding, retained-source, cross-job, or publication recovery defect is established in this round.

## Tests, raw data, and limits

`review-removal-execution-current` passes 18 tests in 43.122 test seconds, with runner wall time 43.310 seconds. It includes the two adapted original controls, executable identity controls, current consumer controls, manager owner controls, real service publication, and actual fresh stock construction.

`review-removal-execution-adjacent` runs five tests: the two new probes fail and three imported runtime controls pass. The imported controls appear because unittest discovers the fixture class imported by the probe module.

`review-removal-execution-adjacent-exact` reruns only the two new probe classes. Both fail again for the stated assertions. Its runner wall time is 1.016 seconds. All stdout, stderr, JSON receipts, and completion markers remain beside this report.

`source-hashes.json` records 14 exact source and test hashes from the reviewed commit. `source/` preserves their bytes. Reproduction modules and safe receipts remain in this directory.

The reviewer changes no product files, commits nothing, and pushes nothing. The review accesses no remote hosts, personal records, memory tools, or journal tools. The constructed sealed runtime is read-only. All changed code, caches, profiles, executable copies, and service definitions belong to disposable synthetic fixtures. Those fixtures clean up their runtime directories and owned units.
