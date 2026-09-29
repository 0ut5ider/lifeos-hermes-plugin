# Patch footprint reduction

Date: 2026-09-29
Scope: Implement the five approved reduction ideas before upstream work.

The earlier corrected bundle contains 20 Hermes patches and nine LifeOS patches. It contains a custom file launcher and a redundant hook lookup definition. The reductions remove those changes, register commands through the existing plugin API, and rebuild the Hermes sequence into eight groups with disjoint file ownership.

The source replay compares every intended source file with a fresh patched checkout. Hermes differs from the earlier corrected bundle in five files: the removed launcher change, its replaced test coverage, the redundant helper removal, the effective provider field on the final-answer hook, and its provider regression tests. LifeOS differs in three files: the task capability probe removal, the model observation adapter, and the integrity command callers. Raw results are in `docs/verification/2026-09-29-patch-footprint/tree-equivalence.json`.

The native model adapter changes from 59 added and 13 removed lines to 28 added and six removed lines. The plugin now resolves the tier. Native LifeOS still owns the warning policy and audit file. The task adapter loses its synthetic probe branch. A digest-verified installation record travels with the native files and participates in update and restore.

The first command fixture pointed the dependency record outside its installation's managed generation directory. Hermes rejected that record. The fixture now copies dependencies into the supported generation layout. An initial source-preparation attempt used a repository whose pinned commit was not reachable after clone. A clean checkout with the tested commit as its selected branch resolves that fixture problem. The source preparation tool also refuses a cloned branch-name collision; this pre-existing limit is unchanged.

The installed command fixture uses two profiles in A, B, A order. It uses a source path with spaces, an apostrophe, and a Unicode character. It makes actual text and image HTTP calls and exercises the native launcher, plugin discovery, selected dependency generation, and strict provider failure behavior. Its deterministic server does not measure actual model quality.

The first broad test run found two synthetic contexts missing `register_cli_command`, an obsolete synthetic TaskGovernance probe fixture, a wrong FailureCapture source path, and missing streaming support in the protocol fixture. The corrected TaskGovernance test runs the native Bun hook with real count 49 and count 50 cases. The HTTP fixture handles streamed completion chunks and rejects the optional Ollama metadata endpoint with HTTP 404.

The required permission, prompt, final-answer, remote-file, and child-routing behavior remains in the bundle. Full 74-hook parity remains open. This package is staged locally. No running gateway or production server changes as part of this reduction.

The named-provider regression initially returned `custom` for the configured `private-lan` endpoint. Hermes already has `effective_runtime_provider` for this distinction. The stop hook now uses that helper. The regression also verifies that an actual fallback provider overrides an earlier requested name. All three cases pass.

The local plugin suite passes 347 tests with 51 environment-dependent skips (398 total). The focused Hermes suite passes 163 tests, with one live SSH test skipped. The Hermes run reports one existing invalid-escape warning in `pm/shell.py`, which this package does not change. Initial host collection failed because the disposable test environment lacked the locked `prompt-toolkit` dependency. Installing that test dependency resolved collection.

Astra found a project-settings regression in the new capability lookup. The main settings lookup missed native TaskGovernance registered in trusted project settings. Its reproduction returned no block in the reduced working tree and a native block in the prior bundle. The fixed lookup uses the effective TaskCreated groups for the session, directory, and backend. It includes trusted local project registrations and excludes remote project hooks from the local native capability contract. Regression tests cover both project settings files, missing records, verified counts, and modified native bytes.

The supplementary native permission run initially failed because its optional Tirith scanner was absent. The fixture now uses the actual locked Tirith binary after SHA-256 verification. The permission case passes with the real scanner and still blocks hardline commands. The unchanged stock launcher suite passes 21 cases, with nine Windows-only cases skipped on Linux. Its initial dashboard case lacked the locked web dependencies; those dependencies were installed only in the disposable test environment.

The final plugin run after the project-settings fix passes 347 tests, with 51 environment-dependent skips (398 total). Astra independently reran 30 focused cases and the installed CLI case. The parent reran its historical patch reconstruction and original task registration reproduction. The review scripts now name baseline commit `3966a42` explicitly so they remain reproducible after this branch is committed. The review has no unresolved confirmed findings.
