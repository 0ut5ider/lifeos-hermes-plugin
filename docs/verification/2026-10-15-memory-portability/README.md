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

The primary final primitive run passes 68 tests. The independent closure review clears the three initial primitive findings. The broader `workflow-current-suite` passes 70 tests. It covers current activation, return, native owner grants, ownership recovery, actual user services, and the fresh actual Hermes constructor. The fresh probe emits only hashes and counts. It does not execute a model turn. The 24 dashboard component checks use an SDK test implementation and do not establish browser acceptance.

The [orchestration review](../../agents/2026-10-15-memory-transition-review/memory-transition-review.md) measures four P2 findings: early drain intent recovery, enabled runtime-linked Pulse removal, cancelled activation retry, and native correction after final reference admission. `primary-transition-red` reproduces all four failures. The fixed `transition-closure` passes 10 tests. It refuses the enabled linked unit layout before publication. It separately verifies persistent disablement and rollback with an actual regular enabled user unit. The [cutover note](../../../notes/2026-10-15-memory-cutover-barrier.md) records the native writer barrier.

The disposable guest is CT110 at `192.168.8.244`. Its unpatched stock dashboard runs without model or Discord delivery. The existing processing VM and guests retain their previous states. `guest.json` and `stock-dashboard.json` contain safe provisioning metadata. The public installation replay has started. No complete integration or detached workflow acceptance is claimed yet.

The subsequent [manager workflow review](../../agents/2026-10-15-memory-workflow-closure/memory-workflow-closure.md) clears the prior four findings and measures four additional issues. A failed activation job can recover another configured activation. An exit before admission blocks recovery. Return preparation can lose its inner and outer recovery bindings. An older dashboard response can restore private text after authentication refusal. The primary reproduces all four Python boundaries and the browser-component ordering failure before applying fixes.

Activation, return, and transition plans now bind the exact operation ID. Preparation recovery cancels only that operation's unapplied plans and archives them privately. A later review can reuse the export. Queued operations expose an owner recovery path. Ordered dashboard requests discard stale responses. `primary-workflow-green` passes 18 controls, including actual child processes and isolated real user services. `workflow-ui-final.stdout` records 25 passing components. The source comments identify protocol fixtures and SDK test implementations; these checks do not establish full browser or model acceptance.

`stock-auth-tests` passes 20 stock-source and release-admission controls. The build now includes an exact Git archive of the pinned unpatched Hermes commit. The package manifest binds its size and digest. Runtime preparation can select that stock source without bridge membership. Complete removal still needs its program, service, recovery, and installed-runtime acceptance. No existing immutable release asset changes.

Complete the detached owner-authorized service workflow, fresh import ownership cutover, complete software removal, and standalone recovery. Then test actual browser controls, source data, real session recall, interruptions, reboot, and retained data in a disposable guest. Obtain the final independent review and qualify one complete package before daily deployment.

The [final workflow review](../../agents/2026-10-15-memory-workflow-final-review/memory-workflow-final-review.md) clears the four manager findings. It finds two earlier bootstrap gaps. The primary independently reproduces four process-exit failures in `bootstrap-red`. Preparation now publishes a complete private directory atomically. Incomplete directories stay outside active operation discovery. They retain private copies without blocking another review. `bootstrap-green` passes 17 controls. `bootstrap-expanded` also tests an exit after the queue directory creation, before its first request. The independent broader `workflow-broad-current` passes 94 tests before this bootstrap change. Complete removal and installed end-to-end acceptance remain pending.

The [bootstrap closure review](../../agents/2026-10-15-memory-bootstrap-closure/memory-bootstrap-closure.md) clears both remaining findings. It tests complete directory publication before and after parent sync and retained inactive-copy isolation. The primary repeats all seven additional controls in `bootstrap-primary-closure`; all pass.

`removal-components` passes 17 tests. The tests cover current semantic configuration, exact native program removal, retained foreign hooks and data, actual service restart with Pulse absent, actual Hermes password authentication, and retained owner policy after active policy removal. The service tests retain inherited protected system overrides. The [service-binding note](../../../notes/2026-10-15-removal-service-bindings.md) records the measured root cause.

The public 0.5.0 integration installs successfully through the actual Hermes web controls in CT110. A read-only installed inventory identifies 1,839 native files, 12 dependency trees, and 74 owned hook registrations. `native-removal-inventory.json` records counts only. The inventory does not mutate installed software or read personal records. The complete removal coordinator, its owner UI, stock runtime construction, standalone recovery launch, and full installed acceptance remain pending.
