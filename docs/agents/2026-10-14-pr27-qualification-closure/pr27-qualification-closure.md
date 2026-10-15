# PR27 qualification closure review

Date: 2026-10-14

Role: Independent qualification review closure

Question: Do the committed guest identity and checkpoint cleanup fixes resolve both P2 findings without a measured regression?

Model: gpt-6.1-sol, high reasoning effort

## Verdict

CLEAR for the reviewed qualification fixes at commit `43e0ab9c`. Both prior P2 findings are resolved. I found no new actionable issue in the narrow closure review.

The product program remains commit `04efe633296eb2b1a1d95561ca6d3e9516cd47dc`, archive SHA-256 `a6dd0e11b8fb1b5ae30345be20c955db02728839f7bc907f60a70944ad392813`. The earlier product review remains CLEAR and is a separate review checkpoint.

This verdict permits the reviewed source to proceed through the remaining actual qualification gates. It does not certify unfinished development acceptance, owner memory turns, final certificate controls, publication, or daily promotion.

## Original brief and review history

The primary requested review of PR27 qualification code and operators without remote actions, memory calls, credential or personal record access, private map access, certificate writes, or constructed completion receipts. The original review at `94ea72dd52a84425bf39f1e482ba64aaddb0c03b` found two P2 issues:

1. The certifier did not bind reboot evidence to source guest 111 or reject explicit production-change claims in rehearsal summaries.
2. The backup operators established their recovery flag only after a successful drain, so a partial drain failure skipped service recovery.

The primary reproduced both findings, retained the failing controls, and committed strict receipt guards plus recovery obligations before both drain attempts. The primary's seven local post-fix controls pass. This closure independently checks the changed code and extends failure-path coverage to both backup operators.

Previous report: `docs/agents/2026-10-14-pr27-qualification-review/pr27-qualification-review.md`.

Previous product report: `docs/agents/2026-10-14-pr27-baseline-review/pr27-baseline-review.md`.

No prior objection remains unresolved in this closure.

## Finding 1 resolution: Guest and production-change guards

The certifier now requires the reboot receipt's source guest to equal 111. It requires an actual JSON false value for `production_guest_changed` in the fresh installation, whole-guest restore, and reboot summaries. The `is False` checks reject numeric zero, null, and the string `false`.

The full certificate control source now includes the wrong reboot guest and three production-change mutations. Those controls can run after the real development receipts exist.

Independent local replay used copies of existing safe receipts and the actual current certifier. I withheld both development completion receipts from every copy. This prevents the replay from creating a release certificate even if the primary completes development acceptance while this review runs.

Results: **8 cases PASS**.

- Unchanged evidence reaches the actual missing development verification gate.
- Reboot source guest 253 refuses with AssertionError before that gate.
- Reboot production change true refuses before that gate.
- Fresh installation production change true refuses before that gate.
- Whole-guest production change true refuses before that gate.
- Reboot production change numeric zero refuses before that gate.
- Fresh installation production change null refuses before that gate.
- Whole-guest production change string `false` refuses before that gate.

No mutation reaches the pending gate. No case creates a certificate. No completion receipt is constructed.

## Finding 2 resolution: Partial drain cleanup

Both `protect_development.py` and `proxmox_rehearsal_restore.py` now establish the recovery obligation immediately before calling the drain action. They clear the obligation only after a successful normal resume. Their finally blocks consult `s.status()['recovery_required']` in the selected native service manager and call `s.resume()` when required.

If cleanup fails while an original failure is active, the operator adds a note to the original exception and preserves that exception. If cleanup is the only failure, it propagates. The nested final block writes the process failure marker in either case.

Independent local control-flow results: **14 cases PASS**, seven per operator.

Each operator was checked for:

- Failure before the drain attempt, with no recovery call.
- Partial drain failure, with a recovery call.
- Partial drain failure plus recovery failure, with the original error preserved and a cleanup note.
- Backup failure after a successful drain, with a recovery call.
- Backup failure plus recovery failure, with the original error preserved and a cleanup note.
- Normal resume failure, followed by a recovery attempt.
- Normal resume failure plus recovery failure, with the original error preserved and a cleanup note.

Every case records failure rather than success. The probes keep marker writes in memory, so they do not write guest completion receipts. They execute the operators' actual local outer try/finally blocks and inject failures at explicit external call boundaries. They do not run Proxmox, services, backups, or guests. This is a control-flow test, not a substitute for an actual backup or service recovery test.

The fixes preserve the existing restore cleanup condition. The disposable restored guest is destroyed only after a completed successful restore verification. The source service recovery obligation is independent of that condition.

## Verification scope and pending execution

Independent closure checks total **22 passing cases**. The raw results contain exact failure locations, call sequences, original errors, and cleanup notes. The reviewed file SHA-256 map identifies the actual source snapshot and remains unchanged when this report is written.

I did not repeat the previous 63 product tests, 13 archive probes, 821 integration tests, or 716 native tests. The primary already reproduced the product review and holds the actual exact-archive test results. The narrow fixes change the qualification certifier and backup operators, not the product archive.

The full certificate control suite remains pending until the real development verification and owner-turn receipts exist. I did not supply replacements for those receipts. I did not run the full acceptance path or write a certificate. Actual development and daily guest state checks remain with the primary.

No new product, operator, or repository evidence change is required by this closure review. I wrote only review artifacts and made no Git or remote operation.

## Artifacts

- `probe_certificate_closure.py`: independent replay of the current certifier with safe receipt mutations.
- `certificate-guard-probes.json`: all eight exact refusal locations.
- `certificate-summary.json` and `certificate.stderr`: replay summary and error output.
- `guard-inputs.tar.gz`: duplicate safe input copies, compressed for retention.
- `probe_backup_cleanup.py`: independent control-flow checks for both backup operators.
- `backup-cleanup-results.json`, `backup-cleanup.stdout`, and `backup-cleanup.stderr`: fourteen failure-path results.
- `reviewed-file-sha256.json`: exact reviewed source identities.
