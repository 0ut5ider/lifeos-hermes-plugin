# Memory portability implementation checks

Date: 2026-10-15. Status: implementation in progress. The daily server remains on qualified 0.5.0.

The [implementation contract](../../memory-portability.md) covers import, portable export, provider return, complete software removal, and final release qualification. These checks verify the first primitives. They do not establish complete service orchestration, removal, browser acceptance, or deployment.

## Current checks

The runner uses the existing qualified 0.5.0 native LifeOS fixture and frozen Hermes test environment. All data created by the tests is synthetic.

1. `import-active` passes 41 test executions. Some imported fixture classes execute twice. The added tests reproduce and fix active-provider refusal and provider/ownership disagreement.
2. `upload-green` passes both authenticated upload and complete import HTTP controls. Uploaded source bytes remain separate from profile memory.
3. `export-http-green` passes six tests for authenticated export and download, provenance, capacity, retained overflow, retirement, and source changes.
4. `portable-bundle-green` verifies retained fact import, literal Hermes delimiters, original references, and private source preservation.
5. `return-green` passes four current-state return tests. The process-exit test terminates a real Python process after its first file publication. Recovery resumes the journal. Writer barriers in these primitive tests are supplied callbacks. Real service admission remains a separate gate.
6. `current-primitives` passes 61 test executions. This checkpoint precedes the additional provenance regression and final shared format preflight.
7. `provenance-green` verifies that a later export contains the original import receipt, including the source digest and occurrence.
8. `ui-component-tests.stdout` records 20 passing component tests. The tests use an SDK test implementation. They are not browser acceptance.

## Independent findings and fixes

The [independent primitive review](../../agents/2026-10-15-portability-primitives-review/portability-primitives-review.md) finds three P2 issues. The primary reproduces all four original controls in `primary-review-red`: two assertion failures and two rejected round trips.

1. Provider return changes aliased lists and plugin entries. The fix detaches each modified branch and preserves unrelated aliases.
2. The export and import format limits disagree. A 1,231,507-byte bundle and a separate 70,027-byte retained occurrence reproduce the two limits. The format now supports bounded 16 MiB bundles and 1 MiB original occurrences. Native fact publication keeps its separate validation limits. Export planning validates the same portable parser before publication.
3. Export overwrites an edit between output publications. The fix records each initial output identity, checks it immediately before publication, and verifies every final output before success.

`primary-review-fixes-confirmed` passes all four corresponding regression controls. Its later-output test creates a private file to exercise the identity conflict. An earlier run refuses that edit through the private-file check instead. Both refusals preserve the edit. The historical failed test output remains available.

## Authorized source data

The `.213` source capture copies two Hermes files under their actual writer locks. Their combined size is 665 bytes. `hermes-source-capture.json` contains only file metadata and digests. The original bytes remain in a private cache outside Git. No source fact has entered `.253`.

The shared `.211` connector returns `integrity_error`. No raw memory file or transcript fallback runs. The failure blocks real `.211` records but does not block synthetic development or the authorized `.213` tests.

## Remaining gates

Complete the detached owner-authorized service workflow, fresh import ownership cutover, complete software removal, and standalone recovery. Then test actual browser controls, source data, real session recall, interruptions, reboot, and retained data in a disposable guest. Obtain the final independent review and qualify one complete package before daily deployment.
