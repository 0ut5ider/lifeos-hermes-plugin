# PR27 development rollback and retry review

Date: 2026-10-15

Role: Independent rollback preservation and retry operator reviewer

Question: Does the rollback verifier prove restored program and configuration state, and does the retry verifier retain its refusal and policy boundaries?

Model: gpt-6.1-sol, high reasoning effort

## Verdict

CLEAR for the reviewed rollback verifier and narrow retry operator change. I found no actionable preservation or refusal defect in this scope.

The product remains `04efe633296eb2b1a1d95561ca6d3e9516cd47dc`, archive SHA-256 `a6dd0e11b8fb1b5ae30345be20c955db02728839f7bc907f60a70944ad392813`. All earlier review verdicts retain their separate scope.

This review does not establish the exact native failure cause, successful retry execution, development acceptance, or certificate qualification. Those execution gates remain pending.

## Scope and source snapshot

The primary requested a read-only review of:

- `verify_development_rollback.py`.
- The changed `verify_development_apply.py`.
- The actual safe rollback and identity review receipts.
- `notes/2026-10-14-development-mount-prerequisite.md` and its policy claims.

The retry verifier differs from the earlier reviewed verifier in exactly two lines: the private output directory and operation identifier. The new operation is `4eac8d1b398e47138d80f8b67b6df596`. `apply-verifier-diff.patch` retains the exact comparison. Both scripts parse successfully, and `reviewed-source-identities.json` records their exact SHA-256 values.

The primary reports that the new operation has actual ready preparation. Owner review and application must still complete through the normal authorized path. This review supplies no replacement for that path.

## Rollback verifier

The verifier reruns the fixed development baseline operator and requires the complete safe baseline to equal the pre-promotion baseline. That baseline includes exact prior bridge identity, model and tier selection hash, credential and owner memory configuration digests, and all three service states with their HOME and profile metadata.

It opens the exact first failed operation, requires `rolled_back`, and requires the exact candidate commit and archive hash. It validates the operation plan, creates a program transaction with the sealed expected entries digest, requires the journal state to equal `restored`, and checks every current target fingerprint against its recorded before fingerprint.

The actual fingerprint implementation rejects redirected and unsafe artifacts and compares file or directory kind, mode, and content identity. A recorded absent target must still be absent. This is stronger than checking only the prior plugin version or an operation status string.

The available actual safe rollback receipt reports PASS for operation `86340dd2f6f8473280cc411f5a3e4102`, all 222 program targets restored, exact verified 0.4.3 prior identity, unchanged model selection and configuration bytes, and all three services and homes preserved. I checked that this safe receipt matches the stated operation and prior release identity. I did not read the private program journal or any credential values.

Independent local rollback controls: **18 cases PASS**.

- Seven baseline equality cases: unchanged input accepts; changed prior release, model selection, credential digest, memory configuration digest, service HOME, or service activity refuse.
- Three journal state cases: restored accepts; applied and applying refuse.
- Eight actual filesystem cases: restored file and recorded absent file accept; changed bytes, changed mode, removed file, symlink replacement, unexpected file, and aliased parent refuse.

These controls execute the actual baseline equality, journal state, and per-target loop statements. The file controls use the real native program fingerprint function and real private temporary files. They do not simulate a successful guest rollback or write a completion receipt.

## Retry verifier

The changed verifier still binds all remote commands to `.252` and derives the status, Python, and verification paths from the exact new identifier. It waits for the selected operation to become applied before it runs preservation verification or owner memory turns. The wait permits only the expected unfinished states and has the existing one-hour bound.

The verifier still checks the actual sealed preservation verifier's returned operation, exact product commit, and archive hash. It runs the existing private-model owner conversations and their actual tool-effect validator only after preservation succeeds. It exports only safe verification receipts and keeps raw controlled conversations on the development guest.

It has no apply, grant, repair, admission, reset, import, or rollback operation. The new private output directory preserves the failed first attempt's operator artifacts.

Independent local retry wait controls: **seven cases PASS**. Wrong identifier, rejected, rolled-back, recovery-required, unknown, expired ready, and expired applying metadata all refuse before preservation verification or memory turns. The controls execute the actual outer try/except code with negative local data and keep marker writes in memory.

## Failure and source-review policy claims

The first operation's safe failure receipt records `MountError` at the native subprocess boundary. It does not contain native stderr. The exact subprocess error remains unknown.

The identity review receipt records an actual authenticated owner prompt preview with no launcher, two current identity sources admitted by the existing source-review policy, two committed reviews, and a later preview with a launcher. It states that identity file bytes did not change, personal data was not imported or reset, daily state did not change, and the retry has not yet been verified.

The note correctly distinguishes the measured missing launcher prerequisite from an established sole cause. It explicitly says that the retained failure metadata does not prove the missing launcher was the only cause. Refreshing the admitted source reviews is therefore an authorized prerequisite correction, and the new exact-package operation remains the test of sufficiency.

I found no claim in the reviewed note or safe receipt that the exact native error is proven or that the retry has passed. This review does not turn the source-review result into application evidence.

## Execution limits

Independent controls total **25 passing cases**. The source hashes remain unchanged when this report is written.

The actual retry, full development acceptance, actual owner conversation proof, and certificate controls remain pending. I did not run a remote command, memory call, or operator against a guest. I read no credentials, private maps, personal records, or raw narration. I edited no product or operator source and made no Git mutation. I wrote no certificate or manufactured completion receipt.

## Artifacts

- `reviewed-source-identities.json`: exact source hashes and syntax results.
- `reviewed-verify_development_rollback.py` and `reviewed-verify_development_apply.py`: exact source snapshots.
- `apply-verifier-diff.patch`: the two-line retry change.
- `probe_rollback_guards.py`, `rollback-guard-results.json`, `.stdout`, and `.stderr`: 18 local rollback controls.
- `probe_retry_wait.py`, `development-wait-results.json`, `retry-wait.stdout`, and `retry-wait.stderr`: seven local retry controls.
- `development-rollback-verification.json` and `development-identity-review.json`: exact safe receipt copies inspected by this review.
