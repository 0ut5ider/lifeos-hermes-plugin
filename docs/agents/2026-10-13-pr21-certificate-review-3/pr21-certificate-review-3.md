Date: 2026-10-13
Agent role: Independent read-only targeted PR reviewer, pr21_release_review
Question: Do the certificate corrections close the three prior P2 findings and reject missing, incomplete, and stale receipts?
Model: GPT-6, Codex harness. A more specific backend suffix is not exposed to this agent.

Reviewed the current certifier at SHA-256 9027f18f5023b86acd397fb5232e5eee05d28ea1eb7b2e780f46032d580a1549, plus verify_owner_turn.py, verify_development_owner_turn.py, their current reports, and the retained reports before identity binding. Repository head: efebe014d8b7e498ed3df7f3576ca620454c221c. The earlier three P2 findings are closed. No new actionable finding was identified in this bounded follow-up.

Owner-turn binding now checks the exact writer, expected profile scope, known synthetic memory reference, and verification_active_identity for the corrected package. Both producer scripts read .hermes/integration-release.json from their selected account home. They assert exact version, commit, and archive identity before publishing the report. Their earlier checks still validate actual remember/search stream contents, matching session identifiers, committed writer and reference, and the candidate-specific synthetic request and content. The fresh and development references remain distinct. I confirmed that the retained original reports exist and every original measurement is unchanged; the new reports only add the observed active identity. I inspected and syntax-checked the producer scripts. The synthetic raw streams and installed guest receipts remain remote, so I did not independently rerun the producer scripts or verify the reported remote execution through SSH.

The certificate requires the exact three expected application service names for update, rollback, recovery, and final update. It requires both update and final update to have applied operation and program-transaction states. Its boot gate requires the exact three unit names. The native installation gate now checks the exact default GitHub URL, the measured native manager revision, and the native Hermes base against the build. Rollback and recovery must restore the measured prior 742a0c33 package identity.

All 14 negative controls refuse before the missing restore gate. These include the original failures and additional binding checks:

- Actual October 9 owner-turn receipt substitution, swapped fresh/development receipts, stale owner active identity, and wrong synthetic memory reference.
- Empty development service maps, one missing development service, empty boot-unit maps, and an unapplied final update.
- Wrong default manager source URL, wrong initial manager revision, and wrong native Hermes base.
- Stale integration commit, incomplete ownership status, and wrong rollback identity.

The current real receipts pass the pre-restore checks only. Running the actual full operator against a temporary copy of the current inputs raises FileNotFoundError for whole-guest-recovery.json. No scratch or repository certificate exists. This control verifies refusal of missing restore evidence. It does not exercise a completed restore, frontend qualification, certificate creation, or full release qualification.

The restore schema and the downstream qualification checks remain consistent with the preceding review. Final acceptance still needs the actual whole-guest receipt, program and artifact coverage, successful operation log, and successful process completion. Public latest acceptance and daily promotion remain separate, explicitly incomplete certificate fields. The running restore is not treated as passed by this review.

Raw controls are in certificate-negative-controls.json. The directory also retains the reviewed certifier and verifier sources, current and original memory verification reports, the correction diff, report-preservation checks, and the actual missing-restore traceback. Controls execute the exact pre-restore statements against copied actual receipts in /tmp, with only the receipt-directory binding changed. No completed restore evidence was constructed or supplied. All three Python operators pass syntax compilation.

I did not repeat the product suite for these documentation-operator changes. The primary agent's independent 45-test canonical archive run remains the product verification. No product code, deployment, release asset, commit, push, or publication changed during this review. No SSH, memory, or journal tool was used.

Adrian's remaining review concerns are the actual off-server restore completion and the later public stable replay. This follow-up establishes that the specified stale and incomplete receipt cases are rejected. It does not establish that the remaining release gates have completed.
