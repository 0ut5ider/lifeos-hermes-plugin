# PR18 qualification evidence review, round 12

Date: 2026-10-13
Agent role: Independent qualification evidence reviewer
Question: Do the archive-bound integration runner and exact derivative checks resolve both round 11 findings?
Model: gpt-6.1-sol
Reviewed repository commit: `6a0a241a0b1227d440938aa7156d8d59b87e5740`
Product baseline: `914ad24b0eea7f0022e75edc815f5be08566d0f9`, unchanged by these observational scripts.
Exact observational script hashes appear below and in `inspected-file-hashes.json`.

## Result

Both round 11 P2 findings are resolved in the reviewed scripts. No additional actionable omission found in this bounded follow-up. All six helper tests pass. The exact version derivative predicate also passes independently on the two actual candidate archives.

The new full archive-bound gate was still running during this review. Its completed JSON receipt was absent. This review clears the source predicates and focused controls. It does not claim full qualification or authorize certificate generation without that receipt.

## Integration artifact binding

The new runner verifies the archive SHA-256 and size, reads its bounded regular-file map, and freshly extracts that archive into a private temporary workspace. It checks every extracted archived file against its content hash and normalized mode before starting tests. Unexpected files and links refuse before execution.

The subprocess uses that extracted package as its working directory and Python search path. Its qualification build receipt points to that same extracted package. After tests, the runner verifies all archived files again. It records the archive SHA-256, archive size, regular-file count, deterministic file-map digest, and successful before/after checks in the completed receipt.

Generated extras are permitted only in the post-test check. The allowance is limited to regular Python bytecode caches with an archived source counterpart and the fixed Hermes bytecode fingerprint file. A bytecode cache without a corresponding archived source refuses. The runner does not delete caches to force acceptance. Archived source files always retain their content and mode checks.

The certification script now requires the new archive-bound receipt. It compares the archive SHA-256 and size with the candidate build, independently computes the archive file map, compares its count and digest, and requires both match flags. It no longer accepts the old unbound integration receipt as its completed gate.

This resolves round 11 finding 1. The actual first archive has 21,085 regular files. Its file-map SHA-256 is `e9b783492b6c8cd9f64f0c7181370bc3827ff11bff07ade98ae4dae7b34fdd7b`.

## Exact derivative checks

`version_derivative()` reads both complete archives rather than relying only on the external delta receipt. It requires identical regular-file names and exactly one first-version occurrence in each of the five declarations. Each second declaration must equal the exact first-version-to-second-version byte replacement.

The helper requires the exact changelog addition. It requires the second main manifest to equal the first manifest with only the new version, new commit, and recalculated bridge and manager file-hash maps. It checks the original version and commit against the expected first identity.

All other regular files must retain the same content hash and normalized mode. Only the explicitly selected native Git index and Git log metadata can differ. Native source manifests and dependency programs fall under the unchanged-file check.

The certification script calls this helper before issuing a second-candidate certificate. This resolves round 11 finding 2. My independent actual-archive call returned both `exact_version_transformations=True` and `native_and_dependency_programs_identical=True`.

The candidate archive digests remain:

- First: `5fe78efb7dc45ee4cf6e49766c7e72c8f64e0d0113fd3643290e75adc6d8ebdb`.
- Second: `6fd4a6af3e1fa37f0b57b8db86daf4b72974d0f0993b4d12cba583c84575cbe6`.

## Independent focused controls

```sh
PYTHONDONTWRITEBYTECODE=1 \
PYTHONPATH=docs/verification/2026-10-13-release-ui-install \
/home/outsider/.cache/lifeos-hermes-managed-20261012/native-test-environment/bin/python \
  -B -W error::ResourceWarning -m unittest -v test_qualification_artifacts
```

Result: Six tests pass in 0.011 seconds, exit 0. stdout is empty. stderr contains the test case results and successful summary.

The controls use actual temporary archives and files. They cover changed archived source, unexpected added source, symlink replacement, bytecode source-counterpart requirements, exact version transformation, a hidden plugin declaration change, and an added dependency field in the main manifest. They do not simulate a complete browser or guest installation.

I also called `version_derivative()` on the actual first and second archive paths from their safe build receipts and calculated the actual first archive file-map digest. `actual-archive-predicate.json` preserves that output. `commands.json` records the focused command and function calls.

## Scope and evidence honesty

The reviewed numeric-update observation now records the expected first release as `before_release` and the second release as the active applied release. It preserves model and tier settings, leaves memory ownership inactive, reports an active dashboard, and reports inactive gateway and Pulse services. I read this receipt without accessing its guest.

The certificate continues to identify first-candidate native and integration test commits for both candidates. It continues to report production qualification as false and public-action acceptance as pending. Whole-guest recovery, memory ownership activation, and daily deployment remain explicitly unverified. Exclusive output creation remains unchanged.

The old unbound gate's success does not substitute for the new bound gate. The primary must obtain the completed bound receipt and all other required results before certificate generation. Public UI and chat trials remain separate subsequent acceptance work.

## Exact inspected hashes

| File | SHA-256 |
| --- | --- |
| `docs/verification/2026-10-13-release-ui-install/qualification_artifacts.py` | `888400be5b2377a1f7bf983768836fa713fa6a366e6e088682a324d5fdaead48` |
| `docs/verification/2026-10-13-release-ui-install/run_archive_bound_integration.py` | `56aa92e30962ceb032698557bb1ad696ec860e0a272641915cababb722cb18e1` |
| `docs/verification/2026-10-13-release-ui-install/test_qualification_artifacts.py` | `dbeb687a04467cac64fd19cbf48b8840b8415ef10e6b8fe95c9e0d0c519d15d7` |
| `docs/verification/2026-10-13-release-ui-install/certify_test_prereleases.py` | `3c38e4dedc33b9b85a81644c3f564f3cfe5b1fd9c78b7245e7ed551fea92ff3e` |
| `docs/verification/2026-10-13-release-ui-install/baseline-preserved-candidate-build.json` | `58b5235bf2cea5af0d1b765bfa310c0dc498885cc20d9b83b280342cf3a37a0c` |
| `docs/verification/2026-10-13-release-ui-install/corrected-numeric-update-candidate-build.json` | `a808081baba714d80845a74aa2eda94c28bde187969ae6d47d092be5b49cab06` |
| `docs/verification/2026-10-13-release-ui-install/corrected-numeric-private-update.json` | `98c9459252205113938b8f18b1423ed9f59b0282ba258a3b0d5cc4f776820c39` |
| `docs/verification/2026-10-13-release-ui-install/native-sealed-914ad24b.json` | `504499c4ee832fca189fa907f0b614687ce3c081d7f9bdabf7d97530848158c5` |


## Artifacts and limits

The report directory contains copies of the four inspected observational scripts, the build and safe observation receipts, exact hashes, complete focused test stdout and stderr, exit receipt, actual archive predicate output, and command metadata.

I did not access guests, run full gates, change product or sealed sources, call memory or journal tools, commit, push, publish, or create certificates. I wrote only the authorized review artifacts. Full gate completion, certificate generation, public-action acceptance, and publication remain with the primary agent.
