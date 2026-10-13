Date: 2026-10-13
Agent role: Independent bounded corrected-prerelease certificate reviewer
Question: Do the corrected prerelease predicates and receipt chain bind actual archive, native, interruption, recovery, and update evidence without overclaiming scope or replacing immutable assets?
Model: Codex GPT-6, inherited parent model. The exact harness model identifier is not exposed in this review context.

Reviewed initial certificate script SHA-256: `0bd49847684efc9247c1078e876e2f7977dae1c40289eab10da711e0408206cb`.
Corrected candidate program commit: `10459df6c2b27bda8911dfd96a25b92bee769c93`.
Corrected candidate archive SHA-256: `fe7a9bfbf1c3f68355fc1125f125fac8250a1f9ccecf95ff697b5979dc3d5474`.
Archive bytes: 119155068.
Scope: only the three new observational scripts and their safe qualification receipt chain. Product review at 10459df6 remains closed.

## Result

Two P2 qualification-predicate omissions require correction before certificate issuance. The actual safe recovery and service receipts pass their intended conditions. I found no altered bytes or failed actual guest case. These findings concern omitted certification guards, not a failed installation or a new product defect.

During this review, the completed archive-bound gate receipt becomes available. I read its successful exit and full 674-test summary, and independently verify its actual archive identity and map. The gate is now recorded as complete by the primary. I did not run the gate, invoke the certifier, create a real certificate, publish an asset, or extract a package.

### P2: Validate the recovery-admission receipt before claiming verified recovery

Location in the reviewed script: `certify_corrected_prerelease.py:38-54`, with the receipt merely listed at line 58 and the verified recovery claim at line 70.

The script checks the forced interruption phase, exit code, commit, and the fresh observation's operation identifier. It does not load private-stage-recovery-admission.json for validation. The file only enters the list whose current bytes are hashed into the certificate.

Trigger: The listed admission receipt records a failed command, a different operation identifier, or a result for an action other than queued recovery, while the separate final observation retains the expected applied release identity.

Impact: The script can issue fresh_interruption_recovery_verified=true while the linked admission receipt contradicts the claimed recovery path. Computing a current hash preserves the contradiction; it does not reject it. The preceding prerelease certifier explicitly requires successful recovery admission and interruption binding, so this weakens the existing evidence chain.

Evidence: The source AST has no load() call for private-stage-recovery-admission.json. `predicate-probe.json` records recovery_admission_loaded_for_validation=false. I do not execute the module's certificate code. The actual current receipt has identifier 4e3386b97a64469a87db22ed8c448849, exit_code=0, empty stderr, and stdout identifying that same queued recover action, so it is compatible with the missing guard.

Minimal correction: Load the admission receipt. Require its identifier to equal the interrupted operation, require exit_code=0 and clean stderr, and parse stdout to require the exact expected queued/recover result for that identifier. Preserve its hash after validation. Keep invalid and substituted admission cases as negative controls.

### P2: Require loaded service definitions, not only inactive service state

Location in the reviewed script: `certify_corrected_prerelease.py:47-48`.

The new applied() predicate requires an active dashboard and inactive gateway/Pulse services. It drops the preceding certifier's LoadState=loaded checks for gateway and Pulse. A systemd unit whose LoadState is not-found can also be inactive.

Trigger: An observation reports an applied release but records missing gateway or Pulse definitions with ActiveState=inactive and LoadState=not-found.

Impact: The qualification predicate accepts an incomplete first-install service setup and can certify the complete installation/update workflow despite the missing prerequisites. This is an omitted acceptance guard. Both actual current observations record loaded, disabled, inactive gateway and Pulse units and an active loaded dashboard.

Reproduction: I compile and execute only the current applied() function's AST against the copied safe fresh-recovery receipt. The genuine receipt passes. A copy with only hermes-gateway.service LoadState changed to not-found also passes. `predicate-probe.json` records missing_gateway_loadstate_accepted=true. The complete certifier and its output-writing statements never execute.

Minimal correction: Require LoadState=loaded for all three expected units before the active/inactive state checks. Keep missing-definition cases for both gateway and Pulse as negative controls. The primary also plans explicit native-publication and program-state consistency guards; this report's finding remains the reproduced missing-unit omission.

## Archive and native evidence binding

Both equality scripts hash each complete archive and compare its size with the corresponding build receipt before reading its file map. They require exact equality of regular-file digest and normalized mode under hermes/, lifeos/, and python-runtime/, excluding Git metadata. The report clearly states that 716 official native tests are reused from the prior program commit and that no new native tests are claimed.

I independently compare the actual original and corrected archives without extraction. All 20,269 selected native and Python-runtime files are identical. Their selected file-map SHA-256 is `21042e8776997e54a7a0c6430dba2cd055bd4c614c53025a3eea29aa6a1412e7`, matching the equality receipt.

I read the actual Hermes source manifest from each archive. Both manifest hashes equal the prior native receipt's `c828676c4915468f8489ae7d572f700115a740e434ac5a4e761771bf74865c69`; both tree identities equal `8cf8822a6573e29a949bd9b0183f9a2fe8082251e02078549fa1876137f3e5fb`. The prior native receipt binds the original archive and commit, records exit 0 and unchanged archived files, and matches the equality receipt's exact receipt hash. Its official-runner output reports 716 passes across 38 files; stderr is empty.

The corrected archive has 21,085 regular files. Its complete file-map SHA-256 is `cfe9d27921e6f9df25e32134ec1bbea076f11eba8270109e205457c62041f4f8`. The completed new integration receipt matches this map, archive hash and size, commit 10459df6, successful exit, and before/after archive-file match flags. Its captured output reports all 674 tests with no skips or ResourceWarning and ends in OK. I verified these predicates rather than relying only on its test count or commit label.

The new certifier retains these archive-bound integration checks, the fixed dashboard asset hash, the retained native receipt hash linkage, and distinct integration/native program commits. I found no additional actionable archive or native test-binding defect in the reviewed scripts and actual chain.

## Actual guest receipt chain and scope claims

The interruption receipt identifies operation 4e3386b97a64469a87db22ed8c448849, programs-published, forced exit 73, and commit 10459df6. The recovery admission identifies the same operation and a successful queued public recover command. The fresh-recovery observation records applied state, exact rc.3 release/archive identity, completed native publication, 11 program targets, preserved model/tier settings and later synthetic data, inactive memory ownership, and expected loaded service states.

The installed-update observation identifies a different operation, 7f013d4698de40448e8823879daa2787, with applied state, the same exact complete release identity, 9 program targets, and the same preservation and service conditions. This is an installed update of the corrected package; this chain is not described as a separate numeric-version or published-input browser acceptance case.

production_qualified=false, whole_guest_recovery_verified=false, memory_ownership_activation_verified=false, and daily_deployment_verified=false correctly limit the certificate. Its synthetic managed-dashboard scope accurately describes these private-input guest trials. test_fixture_only=false describes the intended public release artifact, while public_user_action_acceptance remains PENDING. That combination does not claim that the package has already passed public published-input UI or chat acceptance.

The destination certificate uses exclusive mode x, so the script refuses an existing output rather than replacing it. Existing published rc.1 and rc.2 archives and certificates are not selected as write targets. Public acceptance must remain a separate subsequent immutable checkpoint. I do not broaden these claims to production or credential/memory activation.

## Controls, commands, and raw artifacts

All reviewer commands run from /home/outsider/Projects/Hermes_agent/LifeOS_plugin. The certificate module is never imported or executed.

The predicate component control is:

```sh
PYTHONDONTWRITEBYTECODE=1 \
/home/outsider/.cache/lifeos-hermes-managed-20261012/native-test-environment/bin/python \
  -B -W error::ResourceWarning \
  docs/agents/2026-10-13-pr18-corrected-certificate-review/predicate_probe.py
```

Result: exit 0; the actual applied receipt passes; the missing gateway definition also passes; recovery admission is not loaded for validation. Stderr is empty. Only the applied-function AST runs against copied JSON and in-memory altered data.

The archive/native chain control is:

```sh
PYTHONDONTWRITEBYTECODE=1 \
/home/outsider/.cache/lifeos-hermes-managed-20261012/native-test-environment/bin/python \
  -B -W error::ResourceWarning \
  docs/agents/2026-10-13-pr18-corrected-certificate-review/archive_chain_probe.py
```

Result: exit 0; all actual archive, map, prior source-manifest, native-result, and completed integration-result checks pass. Stderr is empty. No new package is extracted and no certificate is created.

The directory preserves exact initial hashes, copies of the three reviewed scripts and safe receipts, the completed gate receipt and summary, both reviewer control scripts, structured control results, complete stdout/stderr, and commands.json. The copied initial script is the snapshot to which the two findings apply.

The primary subsequently reports that four actual-script adversarial tests produced 11 expected failures before correction: changed admission, service, and native-publication observations were incorrectly accepted. Those are primary-run controls with temporary output, not executions performed by this reviewer. The primary is correcting the guards and will request a second review. This report closes the original snapshot and does not assert that an unreviewed correction is clear.

No product source, guest, Git state, published artifact, credential configuration, memory record, or certificate output changes in this review. I do not call memory/journal tools. The existing product review remains clear at 10459df6. Certificate issuance should wait for the predicate corrections and their repeat review.
