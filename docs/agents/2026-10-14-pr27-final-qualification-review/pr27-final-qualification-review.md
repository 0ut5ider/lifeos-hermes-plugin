# PR27 final qualification operator review

Date: 2026-10-14

Role: Independent development verification and stock provenance reviewer

Question: Do the new development verification operator and actual stock source verifier reject unsafe acceptance, with actual development evidence still pending?

Model: gpt-6.1-sol, high reasoning effort

## Verdict

One P2 finding remains open in `verify_public_stock_source.py`. The new `verify_development_apply.py` has no measured finding in this scope. The previous product, qualification closure, and preparation operator CLEAR verdicts remain separate and unchanged.

Review starting commit: `2909b3ff`.

Product program: `04efe633296eb2b1a1d95561ca6d3e9516cd47dc`.

Product archive SHA-256: `a6dd0e11b8fb1b5ae30345be20c955db02728839f7bc907f60a70944ad392813`.

The actual development preservation receipt, owner conversation receipt, and full certificate control result are absent at the final availability check. This report does not close those execution gates or qualify the release.

## P2: Reject extra executable source before asserting an unpatched stock runtime

Location: `docs/verification/2026-10-14-release-0.5.0/verify_public_stock_source.py`, the archive comparison loop and subsequent stock report.

The verifier proves that each of the 18,243 archived source files matches its installed counterpart. It does not compare the actual runtime file set to the admitted archive contents. An extra executable program can therefore remain in the runtime while the validator still reaches the report that declares zero Hermes patches.

A concrete extra path is `sitecustomize.py`. Python imports this module during normal startup when the runtime directory appears in PYTHONPATH. The stock launcher's environment puts that runtime on PYTHONPATH. An unrecorded startup module can change runtime behavior without editing any archived source file.

Independent measured reproduction:

1. Extract the exact stock source archive whose SHA-256 is `e8acf0dfc6329d85b75c5625412c463798d1cd3ae6507aaf88b717dc74e2c6fc` into an isolated local directory.
2. Add `sitecustomize.py` that only sets a synthetic environment marker. Do not modify any archived source file.
3. Execute the current verifier's actual validation statements with its home path redirected to that directory. Stop before the report assignment and receipt write.
4. Observe that the validator accepts all statements and counts 18,243 source files.
5. Start a separate local Python process with the isolated runtime on PYTHONPATH. Observe that the benign startup module sets the marker.

`stock-extra-source-result.json` records `extra_source_rejected: false` and `extra_startup_module_executed: true`. No release or guest completion receipt is written. The local source extraction is temporary, and the benign extra module does not access a guest, credentials, memory, or private records.

Impact: the public fixture may be called an unpatched stock Hermes runtime while additional startup or imported program code is present. This weakens the claim that the later public installation replay starts from native stock Hermes. This is a qualification proof gap, not evidence that the real `.244` guest contains an extra program.

Expected correction: compare the actual runtime file and link set with an explicit admitted set from the stock source archive and the verified dashboard archive. Permit only the known generated artifacts that the operator intentionally allows. Refuse an extra startup or source module. Add a negative control that keeps every archived source file unchanged but introduces an executable extra path.

I sent this finding to the primary immediately. It does not require stopping the active development worker because it affects the separate public stock qualification gate.

## Development verification operator

The operator binds its remote commands to `.252` and the fixed admitted operation `86340dd2f6f8473280cc411f5a3e4102`. It waits for the actual status file to report the same identifier and an applied state. It allows only ready, queued-apply, and applying while it waits, and the wait has a one-hour bound.

After the applied state, it runs the existing exact program and preservation verifier under the selected operation's Python. It checks the returned operation, exact product commit, and archive SHA before exporting the safe receipt. It then runs the real private-model owner conversations, verifies their actual tool effects, and exports only the safe verification receipt. Raw controlled conversations remain on the development guest.

The operator has no apply, admission, grant, rollback, or repair call. It cannot create the development acceptance proof by running an alternate package or by substituting a completion marker for the actual status and verifier results.

Independent local controls: **seven cases PASS**. Wrong operation identifier, rejected state, rolled-back state, recovery-required state, unknown state, an expired ready wait, and an expired applying wait all stop before preservation verification or memory turns. The controls execute the operator's actual outer try/except block with negative local metadata only. Marker writes stay in memory. No accepted applied receipt is supplied.

I checked that native `cli.write_state` includes the identifier required by the operator, so the wait matches the actual status schema.

## Actual local evidence and pending limits

The available public stock source receipt reports the exact upstream commit, stock archive SHA-256, 18,243 matching source files, zero source links, no manager, no LifeOS installation, and `public_installation_verified: false`. The P2 finding above limits the stronger unpatched runtime claim because the verifier does not reject unrecorded executable source.

The primary reports actual development owner review and apply admission. I did not convert those HTTP responses or queued status into applied acceptance. At the final bounded local availability check:

- `development-verification.json`: absent.
- `development-owner-turn-verification.json`: absent.
- `certificate-negative-controls.json`: absent.

`evidence-availability.json` records that checkpoint. I did not poll repeatedly, construct replacement receipts, run the full certifier, or create a certificate.

The full certifier controls and final evidence closure require the actual development preservation and owner conversation results. The primary can request a closure review after those results and the stock verifier correction exist.

## Brief and retained history

The primary requested a narrow final review while the admitted development application runs. The protected development PBS checkpoint, exact manager bootstrap, and complete candidate preparation already have actual PASS evidence. Prior product review, both P2 qualification fixes, and preparation/daily baseline operators remain CLEAR in their earlier reports.

This reviewer may use local pure controls but must not make remote or memory calls, access credentials or private maps, write certificates, construct guest completion receipts, edit operators or product code, or mutate Git. I complied with those limits. I wrote only review artifacts.

## Artifacts

- `reviewed-source-identities.json`: source hashes and syntax checks.
- `reviewed-verify_development_apply.py` and `reviewed-verify_public_stock_source.py`: exact reviewed source snapshots.
- `probe_stock_extra_source.py`: exact archive provenance and benign extra startup reproduction.
- `stock-extra-source-result.json`, `.stdout`, and `.stderr`: measured extra source acceptance and startup execution.
- `probe_development_wait.py`: seven local development refusal controls.
- `development-wait-results.json`, `.stdout`, and `.stderr`: control results.
- `evidence-availability.json`: actual local receipt availability checkpoint.
