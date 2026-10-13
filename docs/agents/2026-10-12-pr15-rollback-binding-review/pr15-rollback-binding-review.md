Date: 2026-10-12
Agent role: Independent read-only qualification relationship closure reviewer, Cerebo
Question: Does the certificate generator refuse a rollback receipt from a different operation than the verified development update?
Model: gpt-6.1-sol, high reasoning effort.

Adrian, the additional rollback relationship gap is closed. This narrow review has no unresolved actionable finding.

The baseline and initial reviewed HEAD are c2789db9f0c86f490b39084df1eb1f76aa7218b6. I review the working-tree correction to certify_release.py and its fourteen-case regression fixture. The corrected generator SHA-256 is 3c4aad46524588c9858a5dc8d953c8aeb39a09c6094fed0b33975bd3449e1cee. The exact inspected fixture SHA-256 is 4c8bc20f3c1b4ac57d22c2da08c937663964016e81d8796eff4d73807566a7c0. Snapshots in this report directory preserve those bytes independently of later Git changes.

The generator change at docs/verification/2026-10-12-release-0.4.0/certify_release.py:37 adds assert update['operation'] == rollback['operation']. It executes after both receipts have PASS status and before certificate creation. The existing checks still require the update to identify the exact a87e7ae9 archive and the rollback to identify the accepted 0.3.1 release. The new equality requires the rollback to belong to the same managed operation whose corrected update passes qualification.

The fixture now sets its synthetic rollback baseline operation to the operation in the actual update receipt. The added wrong-rollback-operation case changes only the rollback operation. Every other existing receipt, log, and explicitly synthetic future/native gate stays the same between that case and the passing baseline.

I independently run the exact same current fourteen-case fixture against two generator snapshots:

- Original c2789db9 generator: the regression exits one. Exactly one case disagrees with its expectation, wrong-rollback-operation. That case exits zero and writes a certificate, reproducing the gap. All thirteen other cases match their expectations.
- Corrected generator: the regression exits zero, with empty stderr. All fourteen cases match their expectations. The wrong-rollback-operation case exits one and writes no certificate. The synthetic passing baseline still qualifies its temporary fixture. Incomplete-gate refusal and all earlier integration/native/fresh mismatch refusals continue to pass.

The original generator's assertion failure is the expected before-fix regression result, not an unresolved failure. before.stdout, before.stderr, and before.exit preserve it. after.stdout, after.stderr, and after.exit preserve the passing correction. regression-summary.json records the independently checked fourteen-case counts and the exact before-fix mismatch list.

The single added relationship assertion is sufficient for this measured gap. It does not change asset identities, source qualification, catalog compatibility, public installation behavior, native runtime checks, or the operational restore controller. I establish no new actionable issue within this correction.

The actual normal rollback remains pending the whole-guest restore. The fixture's invented rollback and whole-guest gates remain explicitly marked synthetic and exist only in temporary directories. They do not become actual acceptance evidence. The public certificate is absent at inspection. The program archive remains the previously reviewed a87e7ae9 archive according to the supplied release state. This round does not repeat its hash validation, integration suite, native suite, controller, or live acceptance. The primary's reported bound 716-test native success is not independently rerun here.

The report directory contains the complete scoped diff, inspected fixture, both generator snapshots, file hashes, raw regression outputs and exit codes, checked summary, commands, and Git state. Only reviewer artifacts are authored. Every Python command that reads the archive uses PYTHONDONTWRITEBYTECODE=1 and -B. No SSH, controller execution, personal data, credential, memory, journal, product edit, push, merge, or publication occurs.

The code review is clear for the rollback operation binding correction. The primary still owns the actual restore and rollback receipts and the final public qualification. Daily .253 remains on accepted 0.3.1 according to the supplied state.
