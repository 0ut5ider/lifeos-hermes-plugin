# Removal preparation review

Date: 2026-10-15

Role: Independent read-only reviewer.

Question: Does removal preparation bind current state, exact software ownership, retained recovery sources, and other consumers safely?

Model: gpt-6.1-sol, high reasoning effort.

Reviewed commit: `c97c2f6e`, feature/memory-portability.

Disposition: Two measured P2 findings require correction. Four new regression probes fail intentionally for those findings. The supplied preparation, ownership, consumer, bootstrap, and retained-state tests pass: 19 tests in 11.298 seconds.

The main prepare function's installed candidate acceptance remains pending. This review does not certify a complete preparer execution, manager integration, dashboard removal actions, or full release qualification. Their pending status is not itself a finding.

## Findings

### 1. P2: A later input edit can become an accepted before-image while the generated output remains stale

Location: optional/lifeos_release_manager/removal_preparation.py:49 through line 55, and the ProgramTransaction preparation at lines 142 through 145.

The software function reads current configuration and environment data and writes their transformed outputs. ProgramTransaction.prepare later captures each target's before-image independently. The preparer does not bind that before-image to the bytes used for transformation.

An owner edit between these operations therefore becomes the accepted current before-image. The generated output still comes from the earlier bytes. All ordinary transaction checks pass, and publication overwrites the later setting.

Measured sequence:

1. Generate the actual removal software plan through the supplied fixture.
2. Append a new setting to config.yaml and a new setting to .env.
3. Prepare the actual ProgramTransaction from that plan.
4. Apply the transaction.
5. Observe that both later settings disappear.

The transaction reports success. This is not a change after the recorded before-image, so the existing per-publication checks cannot detect it.

The same pattern also applies to transformed native settings unless their admitted source identity is carried into transaction admission. This review directly reproduces configuration and environment loss.

Evidence: current-input-edits.json, review-preparation-boundaries.stderr, and preparation_probes.py, CurrentStateReview.test_later_configuration_and_environment_edits_survive_preparation.

Required correction: Bind every transformed output to the exact input identity from which it was derived. Program transaction admission must refuse a later input identity, rather than adopting it as the before-image for stale generated content. Carry the identity across native settings transformation and qualified program selection as appropriate. Preserve both later edits on refusal.

### 2. P2: Literal consumer matching misses ordinary executable and home-path forms

Location: optional/lifeos_release_manager/removal_consumers.py, unit_files, processes, and hooks.

The consumer checks match absolute path bytes in unit files and command arguments. The hook check also recognizes some literal home forms. Three measured cases evade those checks:

1. A real process executes the account-owned Bun binary with argv[0] equal to bun. The probe verifies /proc/PID/exe resolves to the selected binary. The process scan admits it because the command line contains no absolute selected path.
2. A foreign service uses ExecStart=%h/.local/bin/bun and a %h/.claude program path. The unit scan admits it because it does not normalize the account home specifier.
3. A retained owner hook uses node with a ${HOME}/.claude program path. The hook scan admits it because the braced home form does not match the supported literal checks.

These are explicit consumers of software selected for deletion. The process case uses an actual Bun child outside reviewed service groups. The service and hook cases are direct metadata admission tests. This review does not execute the synthetic foreign service or hook.

Evidence: basename-bun-process.json, home-expanded-service.json, braced-home-hook.json, review-preparation-boundaries.stderr, and preparation_probes.py, ConsumerReview.

Required correction: Inspect the actual executable identity when checking running processes. Normalize the supported home-path forms before checking unit and hook dependencies. Continue to refuse unresolved or unsupported consumer forms when the preparer cannot establish safe removal. Preserve foreign processes, service files, and hook registrations.

## Passing admission and ownership behavior

The supplied return-admission tests use actual native facts and actual return plans. Their verification journals are synthetic admission fixtures, as their file header states. They are not installed end-to-end verification.

Those controls reject another owner, an unverified workflow state, a changed signature, and new native facts after the reviewed export. They permit later built-in memory edits and retain those edits. The return binding includes the exact operation identifier and reviewed export signatures.

Guard ownership checks validate the current mount journal, exact guard file identities, and a complete four-file guard manifest. They refuse changed files, extra guard extensions, pending mounts, and another native binding.

Pulse ownership checks require a historical fresh creation, an applied release record, a validated plan digest, and the exact current Pulse file identity. Their tests refuse later unit edits and non-fresh ownership evidence.

The fixed software plan preserves SOUL.md, built-in memory, workspace data, and current unrelated environment settings. It selects explicit stock launchers and requires an explicit Discord-disable acknowledgement. Finding 1 concerns an edit after transformation, which those stable-input controls do not cover.

## Recovery bootstrap review

The standalone helper freezes standard-library validation code into its command. That code checks the private current marker, exact workflow identity, plan digest, and exact retained manager and bridge file maps before it executes the retained manager worker.

The bootstrap tests refuse changed retained manager code, changed bridge code, a foreign workflow marker, and a public marker. An actual sealed stock runtime executes the generated help command successfully without prompting for a password. That is a command-startup control, not a successful authenticated recovery action.

The prepared-state extraction keeps the original profile for owner grants, validates the retained owner policy, and preserves live owner revocation checks. The actual standalone password authentication remains in the retained manager after source validation.

No additional measured bootstrap or ownership defect is established in this round. The full helper recovery action still requires installed acceptance.

## Primary response and scope boundaries

The primary agent receives all four exact probe names and acknowledges the measured findings. The proposed response carries expected before-image identities into transaction preparation, binds native admitted source identities, checks actual executable paths, and normalizes supported home forms.

Those subsequent changes are outside the captured commit and are not certified by this report. If software changes its return contract to include an expected-before mapping, the closure probe must pass that mapping to ProgramTransaction.prepare. A tuple-unpacking error is not a closure result.

## Method and raw evidence

The reviewer changes no product files, commits nothing, and pushes nothing. The review accesses no remote hosts, personal records, memory tools, or journal tools.

All tests use synthetic profiles and artifacts. The lost-update probe uses actual generated files and actual ProgramTransaction publication. The process probe copies the real Bun executable into the synthetic account and starts it with a basename argv[0]. It verifies the executable identity through /proc and cleans up the child without output. No process or filesystem behavior is replaced with a mock.

source-hashes.json records nine source and test files from c97c2f6e. source/ preserves their exact bytes. preparation_probes.py contains all four reproductions. Runner JSON receipts, stdout, stderr, and completion markers remain beside this report.
