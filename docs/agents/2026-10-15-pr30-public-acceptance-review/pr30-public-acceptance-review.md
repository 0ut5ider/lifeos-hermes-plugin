# PR30 public acceptance review

Date: 2026-10-15

Role: Independent focused code and evidence reviewer

Question: Does PR30 bind the public 0.6.0 installation claims to the actual receipts without changing the initial qualification checkpoint?

Model: gpt-6.1-sol, high reasoning effort

Reviewed pull request: https://github.com/0ut5ider/lifeos-hermes-plugin/pull/30

Reviewed head: `9c886816255bf1226bc3aa606107d48635b281a3`

Base: `d5386d76a5b5ad6fdb7c5350f4aaeee45fb6be7b`

Review status: FINDINGS

## Finding P2: The supplementary acceptance generator accepts contradictory decisive evidence

File: `docs/verification/2026-10-15-release-0.6.0/generate_public_acceptance.py`, lines 40 through 60.

The generator loads nine receipts. It checks only some decisive fields before it writes unconditional acceptance claims. Hashing the remaining receipts binds their bytes but does not establish that their contents support those claims.

Five individual negative controls each returned exit code 0 and wrote a supplementary receipt with `status: PASS`:

1. Change the scan confirmation receipt to `status: FAIL`, `target_was_empty_before_confirmation: false`, and `scanner_disabled: true`. The output still claims native scan confirmation.
2. Change the deployment checkpoint to `status: FAIL`, `release_work_changed_daily: true`, and `personal_data_imported_or_reset: true`. The output still claims that production and personal data did not change.
3. Change the publication receipt to `status: FAIL`, tag `v0.5.0`, a false program commit, and no initial assets. The output still claims selection of the latest stable public release.
4. Change the manager source to an arbitrary private URL with a selected ref. The output still claims the default GitHub URL and default ref.
5. Change the manager's `plugin.yaml` digest to 64 zeros. Its count remains 38, so the output still claims that all manager files were verified.

The measured cause is missing validation before the output at lines 50 through 63. The manager check at line 40 validates a count but does not compare the file map with the qualified program. The scan and deployment receipts receive no field checks. The publication check at line 47 validates only the historical asset count.

Required correction: Validate the decisive scan, deployment, publication, manager source, and manager file-map fields against the qualified checkpoint before the generator writes PASS. Add the measured negative controls to the repeatable acceptance checks. Preserve the initial certificate. The supplementary asset remains unpublished, so correction does not require replacement of a public asset or a product change.

This finding does not show a failed installation or a changed production guest. The current positive receipts contain consistent successful values.

## Verified positive evidence

The reproducible checker completed 19 checks. Fourteen positive checks passed. The five expected rejection checks demonstrated the finding above.

- The PR changes no product code, product tests, version declarations, or package scripts.
- The initial certificate is byte-identical to the base commit. Its SHA-256 remains `e53fa1a02d52637fd9678d6978900c10d3003bb2059c78c689078bc0de3db770`.
- All nine supplementary evidence hashes match the actual local receipt bytes.
- All 38 manager file digests match their actual Git objects at qualified program commit `c86b5887b899ca779afbb217c33843e1ee12c381`.
- The fresh receipt identifies public installation on owned guest 112, operation `a8486ae6890a41ceaf29202cb5dce463`, and 11 sealed program groups.
- The actual model receipt records session `20261015_222532_4ad015`, a successful model turn, and no tool calls. This establishes a model reply, not personal memory activation.
- The post-model receipt binds the fresh receipt hash and the same active identity and model session.
- The preserved model mapping digest matches the fresh pre-application checkpoint and the model receipt.
- The scan receipt states that the initial request returned HTTP 400 with CAUTION. It records explicit native confirmation on an empty target. It does not claim retention of a successful HTTP response. The documented `/proc/self/cgroup` read exists in the exact manager source.
- The actual publication receipt identifies the exact archive and unchanged initial certificate. The actual deployment checkpoint identifies both development and daily as verified 0.5.0.
- The documentation distinguishes published 0.6.0 from deployed 0.5.0. It leaves production promotion and personal memory activation as separate owner actions.
- Positive regeneration in a temporary directory produces the exact checked-in supplementary receipt with clean standard error.

## Post-model operator inspection

`verify_public_after_model.py` checks the actual applied operation, the successful public model receipt, the retained plan, the native mount, sealed program maps, current model choices, and active plugin identity before it writes its receipt. `worker.check_restore` verifies the retained mount and the applied program transaction. The output uses exclusive file creation.

I found no separate measured correctness issue in this operator. I did not execute it because it targets the installed guest and writes a receipt that already exists. I did not run a model or inspect raw memory, narration, credentials, or unrelated logs.

## Reproduction and artifacts

Run from the repository root:

```bash
python -W error -B docs/agents/2026-10-15-pr30-public-acceptance-review/check_public_acceptance.py
```

The checker reads repository receipts and Git objects. It copies the generator and receipts into temporary directories for positive and negative controls. It does not alter release evidence, publish assets, modify guests, or call memory tools.

`review-checks.json` contains every check, all 38 expected and actual manager digests, each subprocess return code, captured standard output and standard error, and the generated receipts. The checker itself is `check_public_acceptance.py`.

The primary agent reported a working-tree documentation correction to `docs/memory-portability.md` during this review. That file is outside the exact reviewed PR head. This report evaluates the specified head and does not claim review of subsequent changes.
