Date: 2026-10-12
Agent role: Independent read-only interruption prerequisite closure reviewer, Cerebo
Question: Does the corrected PR15 certificate generator require and bind the actual interrupted-worker exit proof, while preserving earlier qualification refusal checks?
Model: gpt-6.1-sol, high reasoning effort.

Adrian, the open interruption prerequisite P2 is closed. This final focused review has no unresolved actionable finding.

The review begins at HEAD b2e3444df7c1dd0ed4d002d86e7e23dc8370a23a with the producer relationship and exit-proof corrections in the working tree. The primary commits the corrected evidence during review. The final inspected HEAD is 06cb32686b76c30222297ebf4a89821683f3bd7b. The final committed generator matches the independently tested corrected snapshot byte-for-byte.

The corrected generator snapshot SHA-256 is 2b9302e2e6e767bdbd7b4711057b21959ad3c7d5ed3cf75a828c1d4233d81a32. The before snapshot is the exact generator reviewed in the prior complete-binding round, with all earlier relationship fixes and without the interruption exit prerequisite. Its hash is 7f78c2b0a4dcbd71c5dc45c43ecda90e3433be43fa2501cd3e829d269824a87a. The inspected twenty-nine-case fixture hash is f3e79035c11423f19ca7520a42f062c4e44006bd3677d470440db44e6bb00048. Snapshots preserve the tested bytes independently of later changes.

The generator now loads development-bunfixed-interruption-exit.json before certificate creation. It requires the proof's operation to equal the interrupted recovery operation, its program_commit to equal the exact build head, actual_systemd_exit to equal 73, checkpoint to equal programs-published, status_state to equal applying, and program_transaction_state to equal applied. It includes that actual proof in qualification_receipt_sha256. The preparation/recovery linkage and earlier full/native/fresh/update/rollback/reboot/coverage checks remain unchanged in the exit-proof correction.

I independently run the same twenty-nine-case fixture against both snapshots:

- Before correction, the regression exits one. Exactly seven cases violate their refusal expectations: missing interruption proof and mismatched proof operation, commit, exit code, checkpoint, status, and program transaction state. All twenty-two earlier cases meet their expectations.
- After correction, the regression exits zero with empty stderr. All twenty-nine cases meet their expectations. The synthetic complete baseline accepts; every incomplete or mismatched case refuses.

The prior generator failure is expected characterization of the fixed gap, not an unresolved test failure. Raw before.stdout, before.stderr, before.exit, after.stdout, after.stderr, and after.exit retain all results. summarize_results.py independently verifies the exact mismatch list and writes regression-summary.json.

I also rerun the original three-case actual receipt probe against the corrected snapshot. The baseline copies the actual current proof for operation 14215619fd654d9bab0028abe59b62af. Its temporary certificate succeeds. Omitting the proof exits one and writes no certificate. Copying the actual historical proof naming operation 0c49ceb4d5c2450283012d039aa0b84b under the corrected proof filename also exits one and writes no certificate. Neither real proof receipt is edited.

The three-case probe exits zero with empty stderr. For its passing baseline, it additionally verifies that all fourteen qualification receipt hashes match the actual copied receipt and output bytes, including the interruption exit proof. probe_interruption_proof.py, historical-probe.stdout, historical-probe.stderr, and historical-probe.exit preserve this verification.

All probe baseline/native/future-gate additions remain explicitly synthetic test metadata. They exist only inside temporary fixture directories. The tests do not create actual rollback or whole-guest acceptance evidence, and no generated fixture certificate remains in the repository. The existing actual current interruption proof satisfies the new prerequisite without requiring another live interruption experiment.

The correction is sufficient for the reproduced missing and natural historical receipt acceptance. I establish no additional actionable defect in this bounded closure review. The safe new identity-bound development boot receipt belongs to the primary's actual acceptance work. This reviewer does not repeat the reboot, integration suite, native suite, restore controller, or any live action.

The exact a87e7ae9 program archive remains unchanged by these verification-only corrections. The certificate tests read the immutable archive and exercise its existing hash/source binding. This round does not rebuild or modify the package. Whole-guest restore, normal rollback, and public qualification are still pending according to the supplied release state. The public certificate is absent during inspection, and daily .253 remains on accepted 0.3.1.

Only this reviewer report directory is authored. All archive-reading Python commands use PYTHONDONTWRITEBYTECODE=1 and -B. There are no product edits, SSH calls, credentials, personal data, memory/journal tools, Git mutations, delegation, or publication actions. working-tree-diff.patch, exit-proof-only.patch, inspected-file-hashes.txt, commands.txt, and reviewed-state.txt preserve the scoped code and inspection evidence.

The code review is clear for the interruption proof correction and its bounded regression. The primary still owns the actual whole-guest recovery, normal rollback receipts, and final public qualification. This review does not complete those gates or authorize publication.
