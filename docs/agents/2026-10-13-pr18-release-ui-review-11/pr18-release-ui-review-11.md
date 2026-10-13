# PR18 qualification evidence review, round 11

Date: 2026-10-13
Agent role: Independent qualification evidence reviewer
Question: Does the prerelease certificate script bind each claim to the exact candidate artifacts and report its limited scope honestly?
Model: gpt-6.1-sol
Reviewed repository commit: `6a0a241a0b1227d440938aa7156d8d59b87e5740`
Reviewed untracked certification script SHA-256: `71102a062042b16b45a1dcdcc69a7fbb59b27ad196c294d678f89d43cf9b8528`
Product baseline: Round 10 cleared product code at `914ad24b0eea7f0022e75edc815f5be08566d0f9`.

## Result

Two qualification-check omissions need correction before this script certifies the candidates. I found no evidence of incorrect bytes in the actual archives I inspected. I did not issue certificates, reproduce a changed-artifact experiment, or broaden the product review.

### P2: Bind integration test execution to the exact archive and package bytes

Location: `docs/verification/2026-10-13-release-ui-install/certify_test_prereleases.py:51`, with the receipt producer in `run_sealed_integration.py:12` and its report construction.

The script checks the integration receipt's commit label, successful exit, test count, and output. The integration receipt has no archive digest or verified package-tree fingerprint. The runner executes the separately unpacked `build['package']` directory without authenticating it against the archive or recording an unchanged-source comparison.

A successful integration receipt from different unpacked manager or bridge bytes can therefore satisfy this predicate when it retains the same commit label. The script's separate native archive binding covers Hermes source. It does not bind the complete Python integration tree to those integration test results.

This is a source-proven omission in the qualification predicate. I did not demonstrate changed-byte execution and make no allegation about the running gate. The integration receipt was still missing during this review.

Recommendation: Authenticate the integration execution tree against the certificate-bound archive before tests. Record the exact archive digest and a before/after source identity. Require those identities in certification. A count and commit label alone are insufficient for an exact artifact qualification claim.

### P2: Check exact permitted content changes for the version-only derivative

Location: `docs/verification/2026-10-13-release-ui-install/certify_test_prereleases.py:84` through line 91.

The derivative predicate checks archive labels, native-manifest equality, equality of files outside a seven-file list, and the names of the seven changed files. It does not check the permitted content transformations within that list. The delta receipt contains no assertion of exact version-only transformations within those files.

A different dependency or setting in an allowed `plugin.yaml` is compatible with this predicate. That would change installation behavior while the certificate still carries forward first-candidate tests under a version-only claim.

The actual two archives have the intended declarations: each of the five version declarations is exactly the first declaration with `0.4.2-rc.1` replaced by `0.4.2-rc.2`. Their `DAILY-CANDIDATE.json` differences are limited to `version`, `head`, `manager_files`, and `plugin_files`; native-manifest bindings match. This finding concerns the missing predicate, not a measured behavior change in the candidate.

Recommendation: Recompute and require the exact five version text replacements. Require the main manifest to change only version, commit, and the corresponding authenticated file hashes. Check the expected changelog addition. Check all other archive entries for equality, with explicitly allowed non-executable Git metadata differences.

## Checks that are satisfactory

The script hashes both complete archives and checks their sizes against their build receipts. The native receipt explicitly binds the first archive digest, source-manifest digest, source tree digest, successful official-runner result, and unchanged archived Hermes files. The script checks the fixed dashboard archive digest.

The fresh interruption and recovery checks bind the commit and operation identifier. The recovery observation binds the active archive digest, later synthetic file digest, model settings, dashboard activity, inactive gateway and Pulse units, and `NeedDaemonReload=no`. The private update checks bind the active release identity and its fixed operation identifier.

The certificate reports `production_qualified=False` and its synthetic managed-dashboard scope. It explicitly reports whole-guest recovery, memory ownership activation, and daily deployment as unverified. Public user-action acceptance starts as `PENDING`. The second candidate identifies the first candidate as the native and integration test commit. It does not claim those tests ran again on the second commit.

`test_fixture_only=False` describes the intended public release assets. The synthetic receipt and production scope are stated separately. The existing catalog requires `status=QUALIFIED`, supports explicit prerelease versions, and excludes prereleases from default stable selection. This review does not change that catalog contract or claim production qualification.

The script opens the certificate with mode `x`, so an existing certificate is not replaced. A later public-action acceptance asset must remain a separate immutable checkpoint, as requested.

## Independent checks

1. I read the exact current script, receipt producers, catalog, build receipts, native receipt, fresh recovery receipts, and private update receipt.
2. I checked the committed version delta. It changes five version declarations and the changelog, with no product behavior delta.
3. I independently hashed both archives and checked their sizes.
4. I read the relevant version files directly from both archives and checked the exact version replacements described above.
5. I ran the permitted missing-integration-receipt negative control in a disposable directory. The script raised `FileNotFoundError` at `integration-sealed-914ad24b.json`, before creating any certificate. The temporary fixture contains only copies of the two build receipts. No actual output location was selected.

The first archive SHA-256 is `5fe78efb7dc45ee4cf6e49766c7e72c8f64e0d0113fd3643290e75adc6d8ebdb`, size 119154830 bytes.

The second archive SHA-256 is `6fd4a6af3e1fa37f0b57b8db86daf4b72974d0f0993b4d12cba583c84575cbe6`, size 119160420 bytes.

The integration receipt and second numeric-update observation were absent at the recorded review snapshot. Missing evidence remains a refusal, not successful qualification.

## Exact inspected hashes

| File | SHA-256 |
| --- | --- |
| `docs/verification/2026-10-13-release-ui-install/certify_test_prereleases.py` | `71102a062042b16b45a1dcdcc69a7fbb59b27ad196c294d678f89d43cf9b8528` |
| `docs/verification/2026-10-13-release-ui-install/run_sealed_integration.py` | `a8e370f30c816ad88ef009662fb38c944deddb898505e6c2b2371056afff8717` |
| `docs/verification/2026-10-13-release-ui-install/run_sealed_native.py` | `8043afdbcf27d6af04747e1f6d8917aa0001ea31f375cc5bf41de3f4df9efff7` |
| `docs/verification/2026-10-13-release-ui-install/baseline-preserved-candidate-build.json` | `58b5235bf2cea5af0d1b765bfa310c0dc498885cc20d9b83b280342cf3a37a0c` |
| `docs/verification/2026-10-13-release-ui-install/corrected-numeric-update-candidate-build.json` | `a808081baba714d80845a74aa2eda94c28bde187969ae6d47d092be5b49cab06` |
| `docs/verification/2026-10-13-release-ui-install/native-sealed-914ad24b.json` | `504499c4ee832fca189fa907f0b614687ce3c081d7f9bdabf7d97530848158c5` |
| `docs/verification/2026-10-13-release-ui-install/corrected-numeric-update-version-delta.json` | `7de40be65e1a0157e9627cfcfa2181f1a418369d67fbe78c1c907d8f2e5f76df` |
| `docs/verification/2026-10-13-release-ui-install/baseline-preserved-fresh-interruption.json` | `7eba05b02eb11f8c8c355057f07b659157fa5f78c901cf369793067559d89d7f` |
| `docs/verification/2026-10-13-release-ui-install/baseline-preserved-fresh-recovery.json` | `753dd8f634b2804e3099969d7a828e3f7aa64962f78788d24f8610d8f05aa839` |
| `docs/verification/2026-10-13-release-ui-install/baseline-preserved-recovery-admission.json` | `fae3cc427218ea6d186a53b26253ab322353371d2d4601635897a4fdd1d15bc2` |
| `docs/verification/2026-10-13-release-ui-install/baseline-preserved-private-update.json` | `a215e2b0288c5097ed392f45df82b6a2532a563f3af96380df02e18dcaf2aaa2` |
| `optional/lifeos_release_manager/release_catalog.py` | `20281dd1b1fe5e84d6529ea681e6c6e6928c14867a18b531d04c573cfd19c866` |
| `VERSION` | `f464238371b8c136823251c7707abf6ea576b93353a64ef40cced65d6a22bec7` |
| `CHANGELOG.md` | `97061f9a06fca61c212ea1211e3ae84e0b708b87bdda0a666e1b93ad9912300f` |
| `lifeos_hook_bridge/plugin.yaml` | `fc68b15f1eeee0b1d17548070db87b9cf30fad50dcc4c4380757030737038fba` |
| `optional/lifeos_release_manager/plugin.yaml` | `655ed454a8818960c1f753cef66c42b9366da64a0c744f74730d14f0141318ad` |
| `lifeos_hook_bridge/dashboard/manifest.json` | `0b713528343a3a3bd9dc309898218ad0401125037cf44412890fef100c0bff34` |
| `optional/lifeos_release_manager/dashboard/manifest.json` | `ee0e2e9ea014a65c36cdd056397a0b52d2a2fd52f8ad2619ad2c2ab6db654c70` |


## Artifacts and scope limits

The review directory preserves the exact inspected certification script, receipt producers, safe build and observation receipts, committed delta, all inspected source hashes, direct archive checks, and the missing-receipt negative-control result. These copied inputs preserve the review version if the primary changes the live script afterward.

I did not access guests, run complete gates, edit product or sealed sources, call memory or journal tools, commit, push, publish assets, or generate certificates. The findings require a correction and bounded follow-up review. Full gates, completed numeric update, public UI and chat acceptance, publication, and any production qualification remain with the primary agent.
