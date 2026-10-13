Date: 2026-10-12
Agent role: Independent read-only complete qualification relationship reviewer, Cerebo
Question: Do the remaining interrupted preparation, reboot, and restored-program relationships bind qualification to the corrected release, and can the generator still accept natural stale evidence?
Model: gpt-6.1-sol, high reasoning effort.

Adrian, the eight requested relationship corrections pass independent before/after verification. This round establishes one additional actionable P2 finding: the generator does not require the actual interrupted-worker exit proof before it certifies interruption recovery. The primary acknowledges the finding and plans its correction. The actual current interruption proof is correctly recorded; the defect is missing enforcement at certificate generation.

The initial reviewed HEAD and before generator are b2e3444df7c1dd0ed4d002d86e7e23dc8370a23a. The review covers the working-tree generator, boot collector, and twenty-two-case fixture. The corrected generator snapshot has SHA-256 7f78c2b0a4dcbd71c5dc45c43ecda90e3433be43fa2501cd3e829d269824a87a. The boot collector hash is a5cabb787fc498048fb845498d1ab3d116892868c29743e4de067a4df8ae83d2. The exact fixture hash is f3c5043fa662e86d578eb6adbad13593eb103efb4ddb16898e2f698675017e0e. All snapshots and raw results are in this report directory.

1. P2: Certificate generation can qualify interruption recovery without the actual interruption proof.

   Location: docs/verification/2026-10-12-release-0.4.0/certify_release.py:36. The interrupted receipt checks run through line 42, but never load development-bunfixed-interruption-exit.json. The certificate nevertheless sets development_interruption_recovery_verified to true.

   The preparation and recovery receipts establish a selected operation, exact candidate archive, and restored prior identity. They do not establish that the actual worker exits 73 at programs-published. Those states can also accompany a normal rollback. The existing exit receipt is the producer evidence for the actual interruption boundary, so it is a required prerequisite for the published claim.

   I reproduce the gap with the same inspected generator and a three-case temporary fixture derived from the existing regression. The baseline copies the actual current exit proof, whose operation is 14215619fd654d9bab0028abe59b62af. A second case omits the exit proof altogether. A third copies the actual historical development-interruption-exit.json under the corrected proof filename. That historical receipt names operation 0c49ceb4d5c2450283012d039aa0b84b. No fields in those real proof receipts are edited. Both negative cases still exit zero and create a QUALIFIED certificate. The probe regression exits one because those acceptances contradict its refusal expectations.

   All cases retain explicitly synthetic future/native gate metadata only inside temporary directories. The synthetic gates allow the probe to reach this missing prerequisite. They do not establish actual restore, rollback, or release completion. This reproduction is missing or real stale producer evidence, not hypothetical owner forgery.

   Minimal correction: load development-bunfixed-interruption-exit.json before certification. Require its operation to equal interrupted.operation and its program_commit to equal the exact build head. Require actual_systemd_exit == 73 and checkpoint == 'programs-published'. Include this receipt in qualification_receipt_sha256. Add negative cases for missing proof and mismatched operation, commit, exit code, and checkpoint. The existing actual receipt already records the correct values, so correcting the generator does not require another live interruption experiment.

   Reproduction and raw data: probe_interruption_proof.py, interruption-proof.stdout, interruption-proof.stderr, and interruption-proof.exit. The complete raw output shows all three accepted certificates and the actual operations in the current/historical receipts. All generated certificates are removed with their temporary directories. The primary acknowledges the missing prerequisite in this review round.

Requested correction verification:

- I run the exact same twenty-two-case fixture against the b2e3444d generator and the reviewed corrected snapshot.
- Before correction, the fixture exits one. Exactly eight cases violate their refusal expectations: interrupted operation, interrupted preparation commit/archive/version, boot operation/commit/archive, and program coverage count.
- After correction, the fixture exits zero with empty stderr. All twenty-two cases meet their expectations. The baseline passes; every incomplete or mismatched case refuses. Earlier integration/native/fresh and normal rollback operation checks remain covered and pass.
- regression-summary.json independently verifies those counts and the exact before-fix mismatch list from the raw JSON output.

The generator correctly ties the interrupted recovery operation to its prepared identifier and exact version, commit, and archive hash. It correctly ties the boot operation and active identity to the verified normal update. It requires program_targets == 143. It hashes the interrupted preparation receipt as part of the certificate's evidence set. These changes close the eight measured acceptance cases.

The revised boot collector reads the actual selected identity through the installed CLI, requires verified source identity, compares that identity with the selected applied request, records the operation, and requires the actual current boot ID to differ from its supplied pre-reboot boot ID. It retains enabled/running/zero-restart checks for all three services and the actual Bun version. The collector performs read-only CLI and systemctl observations; it does not start services. The safe new boot receipt contains the expected update operation, exact identity, and different boot IDs. This reviewer does not repeat the live reboot or infer absence of external manual service starts from the collector alone. The primary supplies the no-manual-start procedure evidence.

No additional actionable collector or relationship issue is established within this correction. The interruption exit prerequisite remains the open finding. The public certificate is absent at inspection. Whole-guest restore and normal rollback remain pending according to the supplied state. The immutable a87e7ae9 archive and daily .253 accepted 0.3.1 remain outside this round's mutation scope.

Only this report directory is authored. Every archive-reading Python command uses PYTHONDONTWRITEBYTECODE=1 and -B. There is no integration/native suite repeat, SSH, controller execution, live effect, product edit, credential, personal-data, memory, journal, push, merge, or publication action. The before/after generator failures are expected negative regression results and are retained without alteration.

The primary should close the actual interruption proof prerequisite and retain a final passing negative-case regression. This report does not qualify the release or complete the outstanding live gates.
