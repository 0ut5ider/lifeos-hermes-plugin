# Removal cache closure review

Date: 2026-10-15

Role: Independent read-only safety reviewer.

Question: Do the executable cache and PATH-selected Bun fixes close the previous findings, and do their invocation and binding boundaries preserve exact removal admission?

Model: gpt-6.1-sol, high reasoning effort.

Reviewed commit: `399838ddc13c6eee8ebd512e9abfa7477e1fec93` on `feature/memory-portability`.

Disposition: Both previous findings close under the unchanged original probes. The current suite passes 27 tests. Two additional invocation controls pass against real Python and a private complete copy of the constructed stock runtime. One adjacent P2 finding remains: a contained link can select executable target bytes outside the hashed runtime components.

Complete installed preparation, browser interaction, detached worker acceptance, reboot, and model-turn acceptance remain primary-agent work. This report does not certify them. The fresh-owner connector and second-activation lifecycle investigations are outside this bounded removal review.

## Finding

### P2: Contained executable links can reach unbound target bytes

Location: `optional/lifeos_release_manager/removal_runtime.py:23`, which accepts every link whose resolved target stays inside the fixed runtime root.

The execution identity hashes a fixed set of runtime components. Its link check only requires containment within the broader runtime directory. A link can therefore select a target under another runtime directory whose content is absent from the execution identity.

The measured control uses the actual runtime fixture contract, including every required identity field. It replaces the selected interpreter link with a contained link to `stock-runtime/tools/private-python`. It initially copies the real Python interpreter there and records the execution identity. `_stock` accepts that review.

The test then changes only that target file to a harmless executable that exits with status 94. The selected link stays unchanged. Every hashed component stays unchanged. `_stock` accepts the runtime, and an actual child started through the selected interpreter path exits with status 94.

Safe receipt:

```json
{
  "contained_target": true,
  "execution_identity_unchanged": true,
  "changed_interpreter_admitted": true,
  "selected_command_exit": 94
}
```

Probe: `link_target_probe.LinkTargetReview.test_contained_interpreter_link_cannot_select_unbound_target_bytes`.

Evidence: `contained-unbound-target.json`, `review-removal-cache-link-target.*`, and the reproduction source.

This is an unsupported-layout admission proof. It does not claim the current native builder emits this link layout. A separate read-only inventory of the actual sealed fixture finds 1,068 contained links. All 1,068 ultimate targets lie within hashed, non-excluded components. None require the unbound layout used by the probe.

Required correction: Require every allowed link target to be covered by a hashed, non-excluded component, or include transitive target content in the identity. Directory links and excluded regions require the same check. Root containment alone is insufficient. Refuse the unsupported layout before selection, rather than accepting a review whose executable target bytes can later change without changing the review identity.

## Previous findings and measured closure

The previous review at `a18c27d8` found executable cache omission and an inactive PATH-selected Bun service. `execution_probes_original.py` preserves those probes. `cache_closure.py` contains the same probes with no product-contract adaptation.

The bytecode probe still demonstrates that ordinary isolated Python executes its injected valid cache while source bytes remain unchanged. The corrected runtime admission now refuses those added cache bytes. The unchanged probe passes because the runtime no longer admits the changed executable input.

The Bun probe starts a real oneshot user service through `/usr/bin/env bun` with an explicit private PATH. It proves the selected executable through `process.execPath` and waits until the service is inactive. The corrected consumer scan refuses that service. The actual unit is unique and is removed under the shared fixture lock during cleanup.

These are measured closures. The cache result is not merely a changed test expectation, and the service result does not depend on a currently running Bun process.

The earlier stock-launcher and runtime-linked-service findings remain closed. The explicit preparation before-image findings also remain closed under their previous reports.

## Invocation and cache checks

The runtime identity now includes bytecode under the source, interpreter environment, package-manager bootstrap, dependency tools, and optional contained bytecode directory. The common fingerprint default remains unchanged for unrelated program transactions. The non-executable venv lock and source-root package-manager bookkeeping exclusions remain explicit.

The stock invocation helper adds `-B` and an explicit `-X pycache_prefix` before the isolated command arguments. A real isolated Python child verifies that the prefix is the fixed runtime bytecode path, writes are disabled, and isolated mode remains active. A conflicting ambient cache prefix and write setting do not override those arguments. The child creates no cache directory.

The second invocation control copies the complete actual sealed runtime into a disposable private workflow. It rewrites contained absolute links to the private copy and runs the real stock launcher rewrite. It records the exact execution identity after that preparation.

The control injects a valid timestamp cache for the stock CLI entry point into an external cache prefix. It then starts:

1. `hermes --version`.
2. `hermes-agent --help`.
3. `hermes-acp --help`.
4. The generated retained recovery helper with `--help`.

All commands exit successfully with clean stderr. The external cache does not execute. The retained helper displays recovery and rollback help without authenticating or applying an action. The complete runtime execution identity stays unchanged, and the contained bytecode directory remains absent.

These controls establish command startup and invocation behavior. They do not perform authenticated removal recovery or a model turn. The original constructed sealed runtime remains read-only.

## Current manager and recovery controls

The current suite retains real service publication, actual process-exit recovery, and later built-in memory preservation on rollback. It also retains fresh actual stock constructor verification without a model turn.

Owner controls continue to reject another owner and another workflow, allow exact retained recovery admission after active configuration removal, and keep preparation separate from application. Retained-source validation rejects changed manager or bridge code before execution. Actual native password-provider controls reject incorrect credentials and another owner.

No additional measured owner-binding, cross-job, retained-source, or publication recovery defect is established in this round.

## Raw evidence and limits

`review-removal-cache-current` passes 27 tests in 55.240 test seconds, with runner wall time 55.521 seconds. It includes the two unchanged previous probes, cache controls, consumer controls, actual service publication, retained manager ownership, bootstrap admission, and actual password-provider authentication.

`review-removal-cache-invocation` passes two tests in 30.389 test seconds, with runner wall time 30.539 seconds. `isolated-command.json` and `actual-stock-invocation.json` contain safe invocation receipts. Command output hashes identify the successful startup output without exporting unrelated text.

`review-removal-cache-link-target` fails its one assertion for the finding above, with runner wall time 0.215 seconds. The test uses actual files, links, execution identity, and a real child process.

`actual-stock-link-coverage.json` records the read-only link inventory as counts. `source-hashes.json` records 17 exact source and test hashes from the reviewed commit. `source/` retains the corresponding bytes. All runner receipts, stdout, stderr, and completion markers remain beside this report.

The reviewer changes no product files, makes no commits, and pushes nothing. The review accesses no remote hosts, personal records, memory tools, or journal tools. Every changed source, cache, executable, profile, and service definition belongs to a synthetic fixture. Fixtures clean up their private runtime copies and owned units.
