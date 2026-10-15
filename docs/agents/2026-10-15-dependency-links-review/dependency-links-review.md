# Dependency-link and fault-targeting review

Date: 2026-10-15

Role: Independent read-only reviewer.

Question: Does the contained dependency-link correction preserve exact software-plan admission, and do the disposable fault injector's targeting checks survive optimization?

Model: gpt-6.1-sol, high reasoning effort.

Reviewed product commit: `033af30220ce976ec02d92fbc5ca188eff941aae`, with baseline `1f65a0c9`. The operator fixture is reviewed separately by captured source hash because it is not product code.

Disposition: CLEAR for the dependency correction and the corrected operator checks within their stated context. Forty-three local tests pass cleanly. The original operator assertion issue is measured and closed. No remaining actionable finding is established in this bounded review.

The limits in the prior `final-removal-review` remain in force. These component results do not establish installed removal, authenticated recovery, reboot, or real model-turn acceptance for the new package. An archived `4db55b09` package run remains historical evidence and does not qualify `033af302`.

## Dependency correction

Location: `optional/lifeos_release_manager/removal_preparation.py:50`.

Native inventory already admits contained dependency links and records their exact identities. The old software-plan comprehension fingerprints those same roots with link admission disabled. An ordinary contained dependency link therefore fails during plan assembly, before the native before-image can replace the recomputed value.

The correction passes `allow_links=True` only for paths that are keys in the admitted native dependency map. All other artifacts retain the ordinary regular-file and directory checks. The existing native before-image map still overrides the recomputed identities before ProgramTransaction admission.

This restores agreement between native inventory, software-plan assembly, and ProgramTransaction dependency handling. It does not permit arbitrary symbolic links throughout the program plan. It does not replace the admitted native dependency identity with a later value.

## Independent product controls

`dependency_probes.py` adds five real-filesystem controls:

1. **Baseline reproduction:** The captured baseline module executes against actual synthetic dependency trees. It reproduces the regular-owner-artifact refusal before configuration transformation. No product file is edited to obtain this result.
2. **Combined roots:** The complete software plan contains two distinct dependency roots, including the Pulse Observability directory shape. Actual ProgramTransaction application removes both roots, and actual restoration restores both exact identities. Relative file links and a contained directory link survive. Memory, prompt, and workspace bytes remain unchanged.
3. **Later second-root edit:** An edit after the complete software plan but before transaction admission causes refusal. The transaction publishes no journal. The later bytes remain intact, and the other root stays unchanged.
4. **Cross-root link:** A link from one selected dependency root into the other selected root still refuses. Both roots being selected does not expand the per-package link boundary. The link and target remain intact, and configuration transformation does not start.
5. **Regular program target:** A non-dependency program file replaced by a link still refuses. The correction gives that target no link permission.

The combined transaction journal marks exactly the two dependency entries with `allow_links=True`. Its expected identities match the admitted native identities. The tests do not use mocked filesystem or transaction behavior.

The supplied three regression controls also pass: contained dependency removal and restoration, escape refusal, and refusal of an edit after native inventory. Neighboring inventory and ProgramTransaction controls pass in the same run.

Safe receipts include `baseline-contained-link-refusal.json`, `combined-plan.json`, `later-root-edit.json`, and `cross-root-link-refusal.json`.

## Closed operator targeting issue

Original source: `interrupt_guest_removal_original.py`.

The original fixture uses 13 assertions for destructive admission and targeting conditions. They include root identity, identifier shape, reviewed state, launched unit, MainPID, fragment, process UID, exact job and apply arguments, cgroup, and final receipt and status checks.

Compilation of the unchanged source proves that normal mode contains 13 assertion checks, while optimization levels 1 and 2 contain none. The `pidfd_send_signal` reference remains in all three compiled modes. This measurement compiles source only. It executes no fixture code and sends no signals.

The primary agent replaces those assertions with explicit `require` checks that raise RuntimeError. The corrected source contains no assertion. All 13 require calls remain present under normal compilation and both optimization levels.

The independent final run also executes the actual non-root startup refusal under normal Python, `-O`, and `-OO`. Each invocation refuses at the explicit root check before it reaches guest paths. Those subprocess diagnostics are captured and asserted by the tests. No guest records are read, and no process is signalled.

This closes the measured optimization bypass. `fault-injector-assertions.json`, `fault-injector-corrected-compilation.json`, both captured script versions, the primary red and green output, and the independent final receipt preserve its evidence.

## Operator targeting source assessment

Within the declared operator-controlled disposable guest, the corrected fixture selects one fixed profile and workflow path. It requires the reviewed job and the applying state. Its trigger requires all three active plugin paths to be absent and a compatible publication phase.

The unit name must match that workflow's exact launch shape. The systemd query supplies its active MainPID, cgroup, and fixed transient fragment. The process must have UID 1000 and exact job-path and apply arguments. Its unified cgroup must match the unit metadata. The launch receipt and applying state are checked again before the signal.

The fixture signals through the opened pidfd, rather than a later numeric kill call. A successful signal exits the loop. An error leaves the loop through its failure handler. The descriptor closes in all cases. The loop has a 600-second observation limit, and the systemd query has its own timeout.

The private output directory is new for the label. The fixture writes a signal intent before signalling and a completion receipt afterward. It neither triggers a job nor changes product code.

No additional concrete targeting defect is established. The root signal path is not executed by this reviewer. Host selection remains part of the authorized operator context; this script is not certified for arbitrary hosts or unrelated workflows.

## Preserved failure history

The primary original red run, its first fixture-directory failure, and its corrected five-test run remain copied here as `primary-dependency-links-*`. They are distinguished by their actual receipts, not by their labels.

The first independent 41-test run has one reviewer assertion mismatch. The non-dependency symlink is correctly refused by the existing shared-write gate, but the reviewer test expects the later regular-file-type message. The corrected assertion accepts either existing refusal. No product change addresses that test mismatch. Its original probe and raw output remain preserved as `dependency_probes_initial_regex.py` and `review-initial-assertion-mismatch.*`.

The operator's primary red and green receipts remain separate from the independent compile measurements and final verification.

## Clean verification and provenance

`review-dependency-links-final` passes 43 tests in 7.488 test seconds, with runner wall time 7.646 seconds. Its receipt records process exit zero, final exit zero, and `unhandled_diagnostics: false`. There are no failures or skips.

The run includes the five independent product controls, current preparation, inventory, ProgramTransaction tests, and the two operator safety controls. The operator refusal control checks all three actual startup modes.

`source-hashes.json` records four exact corrected product and test hashes, the exact baseline preparation source hash, both operator source hashes, the operator test source hash, and the reviewer probe hash. `source/` and `baseline/` retain captured product bytes. Runner receipts, stdout, stderr, completion markers, safe measurements, and reproduction sources remain beside this report.

The reviewer edits no product files, makes no commits, stages nothing, and pushes nothing. No remote hosts, personal source records, memory tools, or journal tools are accessed. No process is signalled. All product execution uses private synthetic files and real local transactions. No daily or development deployment changes occur through this review.
