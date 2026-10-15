# PR27 qualification review

Date: 2026-10-14

Role: Independent release qualification and operator safety reviewer

Question: Do the PR27 qualification certifier, restored-program proof, and admission, recovery, and promotion operators reject wrong identities and preserve the selected installations?

Model: gpt-6.1-sol, high reasoning effort

## Verdict

Two P2 findings remain open in the reviewed qualification and operator code. The earlier product review remains CLEAR. The product code has no diff between its reviewed commit and this qualification review commit.

Reviewed qualification commit: `94ea72dd52a84425bf39f1e482ba64aaddb0c03b`.

Product program commit: `04efe633296eb2b1a1d95561ca6d3e9516cd47dc`.

Archive SHA-256: `a6dd0e11b8fb1b5ae30345be20c955db02728839f7bc907f60a70944ad392813`.

PR: https://github.com/0ut5ider/lifeos-hermes-plugin/pull/27

The primary reports one later uncommitted addition: the certificate includes `source_review_report_sha256 = digest(review)`. I read that addition. It binds the existing source report and does not change gate behavior.

## Finding 1, P2: Bind the reboot proof to its guest and reject production-change claims

Location: `docs/verification/2026-10-14-release-0.5.0/certify_release.py:194` through line 196. The fresh installation receipt checks at lines 65 through 77 have the related missing production-change refusal.

The certifier verifies the reboot operation, exact package identity, changed boot identity, selected programs, services, and preserved synthetic memory. It does not check `reboot['source_guest']` or reject `reboot['production_guest_changed']`. A matching operation can exist in a copied guest. The receipt must identify the actual rehearsal guest, 111, before it can prove that the selected source guest rebooted.

I replayed the pinned certifier with copies of the existing safe receipts. I changed only `reboot-verification.json` in each independent case:

1. Set `source_guest` from 111 to 253.
2. Set `production_guest_changed` from false to true.

Both mutations pass every pre-development gate and reach the existing missing `development-verification.json` gate. The unmodified inputs stop at that same pending gate. The replay does not create a certificate, and I do not claim that a complete altered evidence set was certified.

A third case changes `stock-first-install.json` to `production_guest_changed: true`. It also reaches the pending development gate. The stock receipt therefore can explicitly report a production change without the certifier rejecting that claim.

Expected correction: require the reboot source guest to equal 111 and require explicit false production-change fields for the rehearsal summaries. Add negative controls for the wrong reboot guest and production-change claims. The existing real receipts already report guest 111 and no production change. This finding concerns the validator, not an observed production mutation.

Reproduction: run `probe_certificate_guards.py` in this review directory. Inspect `wrong-reboot-source-guest`, `reboot-claims-production-change`, and `fresh-claims-production-change` in `certificate-guard-probes.json`. Each records the refusal location and confirms that no certificate was created.

## Finding 2, P2: Recover a partial development drain when the drain command fails

Location: `docs/verification/2026-10-14-release-0.5.0/protect_development.py:39` and the cleanup at lines 48 through 50.

The operator sets `drained = True` only after the entire remote drain and `verify_stopped` command returns successfully. `ProfileServices.drain` first publishes the stopping transaction, then stops services in sequence. It can raise after stopping part of the selected service group. `verify_stopped` can also fail after the drain completes. In either case, the operator still has `drained == False`, so its finally block skips the recovery command.

The result is an interrupted development checkpoint that can leave the development gateway, dashboard, or Pulse stopped until a separate operator resumes the service transaction. The script writes a failure marker but does not perform its intended cleanup for this failure path.

I executed the pinned operator's exact outer try/finally block with an injected failure at the drain call. The precondition views use the existing safe whole-guest success receipt. The injected drain call raises a RuntimeError to represent the documented partial-drain failure boundary. The measured calls contain only `drain-development`; `recover-development-services` is absent, and the drained flag remains false. The probe runs no remote command and writes no completion receipt. It proves the operator control-flow gap, not a real service failure.

The native service implementation supports this failure model: `profile_services.py:243` persists the stopping document before `_drain`; the method has no automatic resume on exception. `resume` handles a stopping document and performs the existing service recovery.

Expected correction: establish a recovery obligation before the drain attempt. In finally, inspect the selected service transaction and resume it when recovery is required. Preserve the original failure if cleanup also fails. The synthetic `proxmox_rehearsal_restore.py` uses the same flag-after-drain pattern and should use the same safe cleanup rule.

Reproduction: run `probe_checkpoint_drain_failure.py`. See `checkpoint-drain-failure.json`. The first probe attempt lacked a `read_bytes` method on its local receipt view. That probe setup error is retained in `checkpoint-probe-first-setup.stderr`; the corrected probe completes and reproduces the missing cleanup.

## Verified guards and evidence

The pinned certifier independently verifies the exact archive digest and byte count, integration and native package identities, test outputs, source manifest identity, Bun identity, review results, fresh installation identity and owner admission, editor behavior, native update and rollback identity, actual exit-73 interruption, operation states, and complete disconnected restore proof.

The safe restore proof identifies PBS archive `PBS-01:backup/ct/111/2026-10-14T23:59:45Z`, source guest 111, and restored guest 110. The certifier binds the restore, network removal, mount, boot, verification, shutdown, and destroy commands to guest 110. It binds artifact capture and source backup to guest 111. It rejects duplicate operation labels and nonzero operation results.

The restored-program verifier calls the existing `check_restore` path with the sealed program transaction and native mount journal. It checks 221 program targets and eight native mount targets. It verifies credential and owner memory configuration bytes without exporting values. The runtime artifact verifier checks the source and restored maps for all 64,401 artifacts. I did not read the private maps.

The admission and recovery scripts retain owner authentication and operation-bound grants. The actual worker exit is injected through tracing at `checkpoint('programs-published')` while the frozen worker entrypoint still performs admission and file mask setup. Recovery uses the distinct recovery grant and actual selected prior release verification. I found no concrete authorization bypass in these reviewed paths.

The promotion verifier checks the sealed program and mount snapshots, actual `hermes lifeos-version`, exact model and tier selection hash, credential and memory configuration byte hashes, and active service process HOME and profile values. Daily synthetic recall uses authenticated memory tooling rather than reading memory records directly. These execution checks remain with the primary agent.

## Independent probe results

I ran 33 certifier cases against the pinned certifier:

- The unmodified safe inputs refuse at the genuinely missing development verification receipt.
- All 25 existing negative controls that precede development reject before the missing gate.
- Four additional wrong restore guest, source guest, archive, and source map cases reject before the missing gate.
- The three mutations in Finding 1 reach the missing development gate and expose the missing refusals.
- No case writes a certificate. No development completion receipt is constructed.

I parsed all 18 reviewed qualification and operator Python files successfully. I did not repeat the 821 integration tests or 716 native tests in this review. I checked their safe result identities and outputs through the actual certifier prefix. The prior product review independently passed 63 targeted tests and 13 probes; the primary has already reproduced those results.

## Pending execution limits

Development acceptance, its two actual owner memory conversations, the full 29-case certificate controls, and final certificate creation are pending. I did not supply substitute receipts for these gates. A second closure review can confirm the two measured fixes and rerun the full controls after the real development receipts exist.

The review does not certify publication, default public URL replay, daily promotion, or an automatic 07:00 execution. The real receipts reviewed here do not report a production guest change. There is no observed evidence that the wrong guest was rebooted; Finding 1 is a measured validation gap.

## Brief and review history

The primary requested a focused review of the pinned certifier, restored-program verifier, safe guest evidence, and admission, recovery, and promotion operators. The product commit remains the previously reviewed 04efe633 package. The primary continues actual development qualification and explicitly prohibits this reviewer from writing certificates, creating completion receipts, changing product or operators, making remote calls, or accessing memory, credentials, personal records, or private maps.

I preserve the earlier CLEAR product verdict separately in `docs/agents/2026-10-14-pr27-baseline-review/pr27-baseline-review.md`. I sent both measured findings to the primary. No fix response has been reviewed in this report. Both P2 findings remain unresolved at this report checkpoint.

## Artifacts

- `probe_certificate_guards.py`: independent pinned certifier replay.
- `certificate-guard-probes.json`: all 33 measured refusal locations.
- `probe-summary.json` and `probe.stderr`: summary and error output.
- `guard-inputs.tar.gz`: exact isolated safe input copies for the 33 cases.
- `probe_checkpoint_drain_failure.py`: pinned operator cleanup control-flow probe.
- `checkpoint-drain-failure.json`, `.stdout`, and `.stderr`: measured cleanup result.
- `checkpoint-probe-first-setup.stderr`: retained probe setup error.
- `operator-syntax.json`: parse results for 18 files.
- `product-diff.patch`: empty diff confirming no product change since the first review.
