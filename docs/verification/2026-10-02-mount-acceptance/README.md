# Staged mount and authenticated remount acceptance

Date: 2026-10-02

## Publication and recovery

The native mount can write prepared outputs into a private staging directory. The plugin validates the prepared configuration before publication.

The plugin journals the previous contents, digests, and permissions for each target. It publishes the prompt, configuration, environment file, guard files, and optional VersionDrift baseline. It verifies the native mount and Hermes configuration before it records completion.

Recovery checks every target before it restores any target. A later edit causes recovery to stop. Recovery does not overwrite that edit.

A real process-kill test exposed an intermediate recovery state. Atomic restoration creates a file with mode 0600 before recovery restores its previous permissions. A second process can die in that interval. Recovery now accepts the original digest at mode 0600 only while its journal records restoration. It restores and synchronizes the previous permissions.

The focused recovery gate passes 23 cases without skips in `recovery-final.txt`. These cases use native Bun mounting, the actual Hermes configuration checker, real password sessions, and process kills. Systemd operations remain component boundaries in these tests.

## HTTP admission

Native PULSE remount requests use a fixed authenticated local Hermes route. The route uses the verified dashboard account and current installation owner binding. It accepts no account, path, or configuration override. Cross-origin requests are refused. Connector loss does not enable a raw mount fallback.

The plugin page shows `Restore interrupted mount` when the mount journal requires recovery. The owner can recover through that authenticated control.

## Verification limits

The earlier combined selection contains two incorrect module names in `combined.txt`. The corrected selection passes 76 cases with one skipped native TaskGovernance case in `combined-corrected.txt`. The full gate sets the required native hook path and must execute that case.

The live checks below cover service and browser installation, private-model turns, authenticated native routes, and killed-mount recovery. They do not establish complete memory ownership setup, full PULSE interface governance, or the complete release gate. Ownership remains disabled on running installations.

## Bounded regression

The fresh source fixture initially lacks the existing PULSE search dependency. `gate-dependency-failure.txt` records 280 cases with 10 failures and 12 errors. Each failure identifies the missing `minisearch` package. The fixture now links the existing owned PULSE dependency directory.

The corrected `gate-280.txt` passes all 280 cases in 211.886 seconds without skips, failures, errors, or warnings. `gate.done` records exit status 0.

An additional boundary test finds that an unconfigured memory remount can publish files before response binding fails. `unconfigured-remount-before.txt` reproduces that write. The route now validates its configuration and owner binding before mounting. `unconfigured-remount-after.txt` passes all 17 authenticated dashboard and native remount cases.

## Managed runtime and browser installation

The prepared configuration checker starts the installed Hermes dependency environment before it selects the staging directory. It preserves the active Python executable. The focused regression passes 43 cases in 42.315 seconds. The latest bounded `gate.txt` passes 281 cases in 210.250 seconds without skips, failures, errors, or warnings.

An isolated `.212` profile runs its dashboard through a real user service. Chromium signs in through the password form. The browser installs native LifeOS 7.40.4 and completes setup through the plugin controls. The finalization response records a committed mount and a created VersionDrift baseline. Screenshots and response records accompany this document.

The fixture needs two manual preparations. The native memory scaffold must reside under the governed user directory. The configuration must use block YAML because native Mount edits block YAML. The transaction refuses invalid prepared output before it changes live files. These results do not establish automatic ownership setup.

## Live browser, update, and recovery checks

The [browser guide](../../browser-acceptance-212.md) identifies the separate acceptance profile and its entry points. Chromium uses the actual dashboard password form. The native HTTP check verifies eleven admission cases. Their statuses are `401, 200, 200, 200, 200, 200, 400, 400, 404, 403, 401`. The cases cover anonymous access, four native memory views, authorized remount, request overrides, an unexposed route, a foreign origin, and cleared browser credentials. Clearing credentials does not prove revocation of a copied stateless token.

A real killed mount leaves its journal in `applying`. The browser recovery control returns `rolled_back`. The live recovery verifier confirms previous bytes and permissions for all eight targets. It does not reset later user edits.

The browser chat check requires a persisted assistant message from the private local model. The tool check requires the actual terminal result for `pwd`, exit code 0, and a persisted assistant reply. It does not count echoed user prompts or terminal frames as replies.

The actual update service applies the prepared same-revision LifeOS candidate, mounts it, renews its baseline, restarts the gateway, and verifies the installed result. `browser-update.json` records the job ending in `applied`. This check does not establish compatibility with an unseen upstream version.

Two failed update attempts precede that success. One detached worker lacks Bun in its service PATH. The fixed launch binds HOME, HERMES_HOME, PATH, and the installed dependency runtime. The other attempt sees plugin-supplied source files as untracked drift. The baseline now tracks exactly `MemoryAccess.ts` and the capability record when present. Arbitrary untracked files and later edits still cause drift. Both failures restore the prior installation.

The restore button uses a fresh owner grant bound to the update job and restore action. It rejects foreign origins and request overrides. The worker retains its user-data guard. The route checks the same guard before it changes a job. Launch failure revokes the grant and restores the request and status. A live browser restore request refuses the changed snapshot with HTTP 409 and leaves the job in `applied`. A fresh successful browser version restore remains open.

The changed snapshot contains only two aliases of the plugin metadata database. An actual SQLite test shows that opening the current schema rewrites the header while retaining identical rows. The connection opener now sets the schema version only during initialization or migration. The test confirms unchanged database bytes. Historical snapshot digests remain unchanged. The [investigation note](../../../notes/2026-10-02-memory-database-read-bytes.md) records the reproduction.

A second pinned update uses a new job and owner grant under the isolated operating-system account. This operator rehearsal uses the actual detached worker. It does not bypass the browser's refusal to apply an already installed commit. The worker applies and verifies the update. A subsequent browser restore attempt expects success but receives HTTP 409. The only changed paths resolve to native `OBSERVABILITY/config-changes.jsonl`, which a hook appends after the update. The database bytes remain unchanged. `browser-restore-success.txt` retains the failed expectation. `restore-fresh-diff.json` identifies the changed paths. The strict guard protects later audit data. A restore policy that preserves later audit data without reviving retired facts remains open.

## Development recorder acceptance

The private development recorder runs outside the public plugin. Its first setup misses 19 detached terminal outcomes because systemd starts with another HOME. The installed Python startup now names its private configuration. A real installed startup and hook subprocess reproduce and verify that correction. All 30 recorder tests pass without skips.

The corrected live run records ten asynchronous handoffs and ten terminal outcomes. It records 34 successful hook completions and zero incomplete invocations. The full retained archive reports no known loss, capture gaps, or integrity issues. Nine native source fingerprints remain unchanged. The historical 19 incomplete invocations remain in the archive. Completion proves execution, not semantic parity.

## Regression evidence and remaining limits

The initial complete memory run records 592 tests with 25 errors in `memory-regression-fixture-failure.txt`. Every error identifies the same omitted shared fixture method in the wiki and Knowledge HTTP tests. The corrected rerun passes all 592 tests in 760.202 seconds without skips. `memory-regression.txt` and its completion marker preserve that result.

The restore, dashboard, update transaction, and native memory selection passes all 67 cases in 55.490 seconds. The interface selection passes eleven JavaScript cases. The bounded gate before the final database correction passes 288 cases in 231.077 seconds. The later complete regression passes all 600 cases in 726.844 seconds. That run exposes two unclosed connections in its database-byte regression test. The test now closes both connections explicitly and passes with resource warnings treated as errors. The bounded gate reruns the corrected test with its neighboring installation contracts. The historical output retains those warnings.

Automatic recoverable memory ownership setup, remaining reader derivatives, restricted prompt and delivery cases, retained-session reconstruction, reviewed-source page controls, schema rollback compatibility, established-profile trial/import/removal, and independent full release acceptance remain open. The full PULSE interface stays on loopback. The dashboard and narrow native acceptance listener are available only to the local network. Running-installation changes and their reversal are documented in the browser guide.

The final bounded gate passes all 290 cases in 230.708 seconds without skips, errors, failures, or warnings. This run includes the closed database connections and all restore admission cases. The complete 600-case run retains its earlier test-resource warnings as evidence. No complete memory release claim follows from these bounded results.
