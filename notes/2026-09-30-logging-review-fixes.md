# Development recorder: independent review corrections

Date: 2026-09-30. Current status: review corrections verified and deployed on `.212`. Earlier sections retain the findings and their verification sequence.

The [independent baseline review](../docs/agents/2026-09-30-logging-independent-review/logging-independent-review.md) found eight confirmed issues in commit `8995ac2`. The primary agent reproduced the findings, added failing regressions, and implemented the corrections below. No public plugin runtime or compatibility patch changed.

| Finding | Correction | Evidence |
| --- | --- | --- |
| Declared credentials survive in echoed JSON and supported objects | Learn declarations from JSON text, partial fields, bytes, dataclasses, command results, and timeout output before artifact serialization | Primitive fixtures and a real command hook verify all four previously leaking result stages |
| HTTP headers and URL credentials escape recognition | Recognize hyphenated credential headers, URL passwords, credential query and fragment parameters, and echoed values | URL fixtures and an actual local HTTP hook preserve native results and filter stored evidence |
| Known lost events disappear from summaries | Sum the maximum cumulative failure count per run and process; expose gap counts | Three intentional failed writes in two processes produce an explicit loss count of three |
| Damaged data stops analysis | Validate event and reference shapes; catch corrupt deflate data; retain valid events and report issues | Six malformed records and a damaged compressed artifact do not stop reconstruction |
| Different settings origins share a registration identity | Hash the observed origin and execution scope with hook content and positions | Two actual bridges with identical hooks in distinct settings files retain two identities |
| Recorder source drift is unreported | Compare actual source hashes with the configured recorder manifest before installing observers | Intentional drift records a gap and preserves the native hook outcome |
| Host records omit available turn identity | Read the native scalar agent turn ID at surrounding host boundaries | An identity fixture retains both native session and turn IDs |
| Failed hooks appear in a field called completed | Separate terminal outcomes, successful executions, interventions, and failures | A failed-only fixture reports one failure and zero successful executions |

All 21 tests pass locally. Exact output is [primary-fixed-tests.txt](../docs/agents/2026-09-30-logging-independent-review/primary-fixed-tests.txt). Historical baseline probe files remain unchanged so that the failures remain reproducible from the reviewed revision.

The first URL expression caused the existing 1,100,000-character artifact test to remain in its first case for more than 51 seconds. Its unrestricted scheme scan tried overlapping starts in ordinary text. A scheme boundary prevents those overlapping scans. The corrected full suite finishes in 5.678 seconds. The slow process was terminated before any deployment.

## Review probe side effect

The reviewer imported `hermes_bootstrap` with a disposable Hermes home. Runtime preparation installed dependencies in that temporary home but also rebuilt generated products in the shared Hermes source checkout. The probe did not reach its host policy assertions. It was stopped, and its temporary fixtures were removed.

The primary agent verified a clean tracked Git tree and unchanged hashes for all nine inspected runtime sources on `.212`. Both generated products have complete build manifests: `ui-tui/dist/hermes-build.json` and `hermes_cli/web_dist/hermes-build.json`. The web manifest timestamp is 15:39:02 UTC. The dashboard returns HTTP 200 at its login page and HTTP 401 for an unauthenticated configuration API request. The generated products remain in place. Their prior ignored-file hashes were unavailable, so this is a documented rebuild, not a claim that their bytes remained unchanged.

Future read-only host probes must add the existing dependency site directly. Importing bootstrap under a temporary home does not isolate generated build output. No `.211` or `.213` system was accessed or modified during this review.

## Remaining limits

Existing private artifacts are immutable. Improved filtering protects new capture and does not sanitize historical artifacts retroactively. Inspect historical data with private, count-only checks before considering any cleanup. Do not publish raw artifacts or rewrite them without preserving reference integrity.

Known loss counts cannot reveal a process that fails before its first successful write or after its last successful write. Registration inventory counts describe observed versions across all captured runs. Completed execution still does not prove semantic parity. Comparative overhead and a complete host permission matrix remain separate verification work.

## Follow-up review corrections

The second review confirmed that remote protocol frames could hide an echoed credential in base64. The recorder now decodes all protocol fields, learns their credential declarations, and only then redacts and re-encodes the captured representation. The native wire remains unchanged. The primary agent reran the actual native remote hook probe. It reports no stored credential and the same native result.

The analyzer now rejects registration fields that SQLite cannot store, reports malformed inventories, and validates signed 64-bit bounds for indexed numeric fields. Valid events remain searchable after these errors. Three added regressions fail before the corrections and pass afterward. All 24 local tests pass. A further independent review and deployment validation remain pending.

A first staged test attempt on `.212` imported the previous recorder package from the account startup file despite capture being disabled. Disabling observation does not prevent Python package import. The staged test uses a clean virtual environment and the staged working directory to avoid that cached package. Failed staged outputs are retained as diagnostic evidence.

## Third review corrections

A fresh reviewer reproduced a declared Bearer authorization value whose bare token echo survived. Credential discovery now learns the token body before filtering supported evidence. The primary regression fails against the prior code. The reviewer independently verifies a real hook: six leaking stages before the correction, no leaking stages afterward, and unchanged native results.

The reviewer also found a checksum cache keyed only by artifact path. A later reference with a different expected digest could pass without validation. The cache now keys by path and expected digest. A failed checksum prevents that inventory from adding registrations. The primary regression fails before the correction. The suite now contains 26 tests. Another independent closure review remains pending.

A staging command quoting error also extracted a development copy and a symlink into the `.212` login account's home. Those files were moved to the private directory `/home/outsider/lifeos-capture-staging-command-20260930/`. They are inactive diagnostic copies. The corrected staging command runs inside the intended test account. No service or native source changed through this failed command.

## Fourth review corrections

The next reviewer confirmed that Cookie and Set-Cookie declarations filtered the header but not its session value echoed in the response body. The recorder now learns individual cookie values with the standard library cookie parser. A failing regression covers both header forms. The real HTTP suite also checks a session-cookie echo in decoded response bytes. The primary agent reran the reviewer's loopback HTTP probe and observed no leaking stage with unchanged native outcomes. A fresh review remains required after this correction.

The fourth reviewer also reproduced Basic authorization component echoes with a real command hook. Discovery now learns the encoded credentials and the decoded password from named Authorization and Proxy-Authorization values. Invalid base64 remains a safe unsupported declaration. The primary agent reproduced both failures before correction, reran the actual cookie and Basic hook probes after correction, and observed no echo leaks with unchanged native results. All 28 local tests pass in 6.260 seconds. Another independent protocol review is pending.

## Fifth review corrections

The protocol review verified single-cookie and Basic corrections, then reproduced two Set-Cookie headers whose second value disappeared in a dictionary conversion. The observer now keeps all response header values before credential discovery. The actual HTTP regression fails before the correction and passes afterward with unchanged native outcomes.

The primary agent also reproduced a shared-container declaration issue. The same list first visited under an ordinary field and later under an API key field skipped credential learning. Cycle tracking now includes credential context and the field name. A new regression fails before correction and passes afterward. All 29 local tests pass in 5.834 seconds. The reviewer is checking the corrected snapshot in a separate closure report.

## Review gate and deployment complete

The [corrected protocol closure review](../docs/agents/2026-09-30-logging-protocol-closure/logging-protocol-closure.md) independently verifies recorder commit `d7758db`. It reports no meaningful confirmed open findings within the bounded logging review. All 29 tests pass independently in 6.490 seconds. The primary agent reran the actual hook probes and the alias/cycle probes. The isolated `.212` suite passes in 5.850 seconds.

The reviewed recorder is deployed. The [final deployment verification](../docs/verification/2026-09-30-reviewed-capture/verified.json) confirms both running service processes loaded the reviewed manifest, all nine native source fingerprints remain unchanged, and configuration and capture-root modes remain 0600 and 0700. At the snapshot there are 1,236 events, zero reported losses, zero capture gaps, zero integrity issues, and zero incomplete invocations. The 149 registration identities form a historical union of observed versions, not 149 installed native hooks.

No public plugin runtime or compatibility patch changed. No push occurred. `.211` and `.213` remain unchanged. Historical artifacts remain immutable and have not been retroactively sanitized. A new live user turn after this restart has not been used to verify host turn IDs or Discord delivery.

### Launcher side effect correction and recovery

Correction to the earlier side-effect account: the bootstrap probe also rewrote two ignored native launchers, `.hermes/bin/hermes` and `.hermes/bin/hermes-acp`, to reference the Python interpreter inside its temporary Hermes home. After that temporary directory was removed, existing service processes kept running. Their next restart exited 127 because that interpreter no longer existed. The tracked tree and nine inspected source hashes were insufficient to detect this launcher change.

The deployment initially treated a transient `active` state as success and printed service process IDs of zero. The subsequent health check caught the failure. That initial JSON remains diagnostic evidence, not the final deployment result. The deployment helper now requires nonzero, stable process IDs before reporting service startup success.

The primary agent backed up both launchers and restored only the interpreter path to the existing managed account Python. Native launcher code and service configuration remain otherwise unchanged. The gateway and dashboard then start successfully with zero restart counts. The dashboard login request finishes at HTTP 200 and its unauthenticated configuration API returns HTTP 401.

Private rollback backups are recorded in [deployment.json](../docs/verification/2026-09-30-reviewed-capture/deployment.json) and [launcher-recovery.json](../docs/verification/2026-09-30-reviewed-capture/launcher-recovery.json). Restoring the old recorder requires restoring its corresponding configuration manifest and restarting both services. Keep the corrected launchers: their backups intentionally preserve the broken temporary interpreter path. The generated UI products remain from the earlier documented rebuild; their prior ignored-file hashes are unavailable.
