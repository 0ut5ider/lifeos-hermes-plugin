Date: 2026-09-30
Reviewer role: Independent code and deployment reviewer
Question: What defects, missed evidence, behavior changes, misleading analysis, privacy leaks, and deployment risks did the development recorder implementation and prior review miss?
Model: GPT-6 via Codex, inherited from the parent agent. A more specific service model identifier is not exposed to this reviewer.

## Reviewed state and recommendation

This report reviews commit `8995ac21344eac801cd00fc86b3c58e299f5627a` on `feature/development-capture`. Local probes load a temporary copy of that commit's recorder source. Remote probes use the deployed recorder source before the primary agent's fixes. The primary agent changes implementation concurrently after receiving these findings. This report does not certify those changes.

The baseline recorder has a confirmed credential leak in real command hook capture. Its analyzer can omit reported capture losses, stop on corrupted input, and merge registration coverage across settings origins. Its own source manifest is recorded without validation. These issues require fixes before its health summaries can support later parity work.

I did not establish a new runtime behavior change in the completed baseline versus traced hook probes. The recognizable credential leak is a privacy defect even though ordinary hook decisions remained unchanged.

## Verification and raw evidence

| Evidence | Result | Scope |
| --- | --- | --- |
| `local-tests.txt` | 11 tests passed in 3.769 seconds | Existing local suite, before concurrent edits |
| `remote-tests.txt` | 11 tests passed in 3.825 seconds | Deployed .212 recorder, managed base Python |
| `local-probes.json` | Confirmed defects below | Isolated baseline source, synthetic artifacts, real hook subprocess |
| `remote-probes.json` | Same core defects reproduced | Private temporary fixtures on .212, managed Python 3.14.7 |
| `deployment-metadata.json` | 1,180 events; zero literal known-credential matches | Read-only aggregation; no production artifact content exported |
| `host-effects-stderr.txt` | Probe aborted during runtime preparation | No completed native host effect assertion |

`independent_probes.py` contains the reproducible synthetic probes. `deployment_metadata.py` contains the read-only deployment aggregation. The known credential scan checks account .env credential literals in referenced artifact text. It does not recognize every credential, decode arbitrary unrelated encodings, or establish that old artifacts are free of the defects below.

Remote test processes start with `HERMES_HOOK_CAPTURE_CONFIG` pointing at a private temporary `{"enabled":false}` configuration. Explicit installation then targets synthetic capture roots. Production prompts, conversations, output bodies, and credentials remain on .212. No memory or journal tools were called. No implementation files were edited, committed, or pushed by this reviewer.

## Severity-ranked confirmed findings

### P1: Declared credentials leak through echoed JSON and supported object representations

Baseline locations: `development/hook_capture/store.py:25`, `:36`, `:43`, `:66`, `:76`, `:108`; command result capture at `development/hook_capture/instrument.py:590` and `:262`.

`declared_secrets` walks dictionaries, lists, and tuples. `safe` also understands JSON strings, bytes, CompletedProcess objects, exceptions, and dataclasses. The two walks disagree. A credential field inside one of those supported representations is redacted, but its value is not learned before other fields are serialized.

Reproduction: a real hook process prints JSON with `api_key=SYNTHETIC-CREDENTIAL-529841` and `echo` set to the same value. The credential field becomes `[REDACTED]`. The echoed value is stored in artifacts referenced by `process.completed`, `run_command.returned`, `hook.completed`, and `response.parsed.entered`. The later parsed dictionary learns the value, after those immutable artifacts already exist.

Both local and .212 actual hook probes return exit code 0 and identical baseline versus traced outcomes. Their output explicitly lists all four leaking stages. Separate dataclass and CompletedProcess artifact probes reproduce the same mismatch. This is a recognizable declared credential, rather than an unknown secret appearing only in arbitrary prose.

Smallest recommended fix: collect credentials recursively from the same supported shapes as `safe`, including parsed JSON and partial JSON fields, before serializing an artifact. Handle cycles without changing application behavior. Add a real subprocess-output regression, because a primitive `safe` test does not cover the order in which runtime artifacts are written. The fix protects future capture; historical artifact cleanup or replacement needs a separate verified procedure.

### P1: Recognizable HTTP headers and URL credentials bypass structural filtering

Baseline locations: `development/hook_capture/store.py:20`, `:43`; HTTP request capture at `development/hook_capture/instrument.py:626`; hook configuration inventory at `:178`.

The sensitive-name expression accepts underscore separators but misses `X-API-Key`. URL strings receive no userinfo or query parsing. The synthetic probes confirm that an unseeded `X-API-Key` value, an HTTP URL password, and an `access_token` query value remain in `safe` output.

The runtime impact is direct: HTTP request headers are captured, and hook URLs are retained in inventory and call arguments. A local hook such as `http://localhost/path?access_token=<credential>` passes the native loopback restriction and can store its recognizable credential before any HTTP request succeeds. URL credentials can also appear in ordinary tool output. No actual unknown production credential was exported or reported in this review.

Smallest recommended fix: recognize HTTP header separators and credential URL userinfo/query fields, learn their values before sibling output is processed, and redact only stored representations. Add a real local HTTP fixture after the primitive regressions.

### P2: A zero-issue summary can hide recorder failures already reported in events

Baseline locations: `development/hook_capture/store.py:144`, `:151`; `development/hook_capture/analysis.py:74`.

The recorder counts an artifact failure and writes `prior_capture_failures` into a subsequent successful event. The analyzer ignores that field. In the synthetic probe, a NaN artifact fails with ValueError and a cyclic artifact fails with RecursionError. A later event records `prior_capture_failures=2`, but the summary reports zero incomplete invocations, empty integrity issues, and no capture-loss count.

This makes the earlier zero-gap snapshot weaker evidence than its wording suggests. It establishes the absence of the error categories that the old analyzer checks; it does not establish complete capture.

Smallest recommended fix: aggregate the maximum reported failure count per run and process, expose it explicitly, and consider sequence discontinuities independently. Do not sum the cumulative field on every event. State the remaining limit: a process that loses every event or exits before its next successful write cannot report its final count through that mechanism.

### P2: Malformed records and corrupt deflate data abort analysis

Baseline locations: `development/hook_capture/analysis.py:42`, `:45`, `:52`, `:55`, `:68`, `:69`.

The code assumes the top-level JSON and data_ref are mappings. It binds unchecked event fields to SQLite. It catches common gzip errors but omits zlib.error.

The isolated probes reproduce four failures: a complete JSONL line containing `[]` or `null` raises AttributeError; a nonempty array data_ref raises AttributeError; an array status raises sqlite3.ProgrammingError; and a damaged gzip deflate payload raises zlib.error. All cases stop index reconstruction instead of recording an issue and continuing through the remaining evidence.

Smallest recommended fix: validate event and reference shapes before dereferencing or binding them, catch the documented decompression error types, record a sanitized issue, and continue with valid records. Add a fixture with one damaged record followed by one valid record, so a regression test proves recovery rather than only exception suppression.

### P2: Registration IDs merge identical hook lists from different settings origins

Baseline locations: `development/hook_capture/instrument.py:178`, `:182`, `:184`, `:219`; `development/hook_capture/analysis.py:62` and `:90`.

The inventory digest includes hook group content and remote workspace details, but local settings origin is computed only after the digest. Registration IDs use that digest, event, group position, and hook position. Two identical local hook lists in `project-a/settings.json` and `project-b/settings.json` therefore receive the same registration ID.

The probe observes two distinct origins, one distinct registration ID, and one indexed registration. SQLite keeps the first origin through INSERT OR IGNORE. If one origin executes, coverage for the other can appear exercised even though it never ran. This extends the prior review's remote-scope concern to local origins and establishes the failure with data.

Smallest recommended fix: include observed origin and execution scope in registration identity before hashing. Preserve distinct duplicate hook positions. Decide explicitly whether identity is stable across runs; do not use a run UUID as a substitute for settings origin.

### P2: Recorder source drift is not checked against the stored manifest

Baseline locations: `development/hook_capture/setup.py:49`; `development/hook_capture/instrument.py:690`, `:706`, `:708`, `:733`.

The installer stores `capture_sources`, but activation never recomputes or compares it. The import loader checks pinned Hermes and plugin sources only. The deliberate drift fixture sets the expected instrument.py hash to 64 zero characters. Hook instrumentation still activates and completes with zero capture-gap events, locally and on .212.

An overlay source change can therefore make process.initialized repeat an old configured manifest while executing different observer code. Checking only the manifest copied into a process artifact cannot establish the observer version that ran.

The read-only deployment snapshot separately compares current files with the actual configuration and finds that they match before fixes. This is a deployment risk and missing guard, rather than proof that the current .212 source had already drifted.

Smallest recommended fix: compute the loaded observer source manifest at activation, record actual and expected provenance, and report any mismatch. Disable stale observer transformations while letting native runtime operation proceed. Validate the intentional drift fixture separately from ordinary hook capture tests; a rejected drift configuration should no longer activate hooks.

### P2: Host context and enforcement boundaries omit the available turn identity

Baseline location: `development/hook_capture/instrument.py:61`, particularly `:66` to `:68`.

When a function receives an agent object, identity reads its session_id but not its native `_current_turn_id`. Most observed host functions receive their turn identity through the agent. The deployed host's `agent/inline_tool_executors.py:18` to `:24` confirms that Hermes itself reads this field for tool hook IDs.

Read-only production metadata confirms that all 3 entered and 3 returned build_api_messages events, both entered and returned apply_stop_gates pairs, and the one dispatch_authorized_once/commit_tool_result pair have session identity but no turn identity. Nested pre-tool hook dispatch records do carry a turn ID. Resetting each wrapper context loses that nested identity before the surrounding host boundary returns.

For a session with several turns, matching actual model context and stop enforcement to a specific hook turn becomes less direct and can require time-based inference. The current single Discord example hides this gap because the outer message ID supplies another correlation key.

Smallest recommended fix: read documented native turn identity from agent objects, with scalar shape checks, and include it at the surrounding host boundaries. Test multiple turns in one session and concurrent tool calls. This is an evidence defect, not a demonstrated host policy change.

### P3: Failed hooks are included in the field named completed

Baseline locations: `development/hook_capture/analysis.py:83` to `:86`.

The query counts both hook.completed and hook.failed, then labels the count `completed`. The isolated failed-only fixture reports `hooks[0].completed=1` while its only status is exception. Status totals preserve the failure elsewhere, but consumers of the hook table can misread it as successful completion.

Smallest recommended fix: name the combined count terminal_outcomes and expose successful completion and failure separately. Keep latency calculations explicit about which outcomes they include.

## Behavior preservation, evidence limits, and public packaging

The completed existing tests verify real hook subprocess decisions, timeout evidence, detached fallback execution, HTTP read limits, duplicate registration positions, parser correlation, and selective thread context forwarding. The independent credential probe also confirms equal native outcomes. These checks do not establish every in-process HTTP extension behavior, all concurrent callbacks, comparative callback-budget impact, trusted remote project selection, or every permission/context path.

The global HTTP observer returns a Response proxy that supplies read and attribute access but not every special method of the original response. Iteration and isinstance checks inside an unusual backend are a hypothesis for behavior changes, not a confirmed native bridge defect. The inspected bridge uses the supplied context manager and read methods, which the existing test covers.

AST import transformation and some transport bookkeeping occur outside optional-observer recovery boundaries. The pinned native sources constrain those paths. I did not construct a realistic supported-input case that changes native behavior there; broad fail-open claims still need targeted future tests rather than an assurance based only on storage failure.

The public install command in README.md selects the `lifeos_hook_bridge/` subdirectory. The recorder package, startup installer, and capture roots are outside it. No recorder source or raw capture directory is present under that runtime subtree. This static boundary check passes. I did not execute a public installer or publish a package during this review.

I read the historical implementation review after performing the independent probes. Its previously fixed parser-shape, encoded-frame, callback-event, Discord-admission, and remote terminal-event findings do not explain away the new results. The deployment note already states that 36/74 registrations and successful execution do not establish semantic parity. Keep that qualification.

## Aborted host probe and unintended external effect

`host_effect_probe.py` is the historical aborted probe, not a successful test. It sets a disposable HERMES_HOME, then imports hermes_bootstrap. That import starts runtime preparation for the disposable home. The final stderr records dependency preparation, TUI build completion, web UI build completion, and `Code updated!`. The exact TUI output path was not established by this reviewer; the primary agent was notified to assess it as well.

Process inspection also observed source_completion invoking `scripts/build/web.mjs` with output `/home/lifeos-hermes/workspace/hermes-agent/hermes_cli/web_dist`. This can write generated files in the shared host checkout, beyond the intended temporary fixture. I stopped the synthetic process tree promptly and notified the primary agent. The probe never reached native permission or context assertions. Both host-effects output files must be interpreted accordingly.

After stopping the probe, `git status --short` for the host checkout was empty. That does not prove ignored generated files were unchanged. The primary agent is checking generated files and dashboard health independently. I did not restore or rebuild them. The two known temporary fixture directories were removed. No service restart, server configuration edit, Discord message, or .211/.213 access was performed by this reviewer.

The primary agent subsequently reported a clean tracked Git tree, all nine runtime fingerprints unchanged, dashboard root HTTP 200 and unauthenticated API HTTP 401. It found a complete web_dist manifest with build timestamp 15:39:02 UTC. The primary will preserve the rebuilt assets and document this outside-Git change, rather than restore an unknown prior generated state. I did not independently repeat those follow-up checks.

For a future isolated host probe, use the already selected dependency site directly and avoid hermes_bootstrap under a new HERMES_HOME. The primary agent requested no further live host probes during this review.

## What requires Adrian's review

The highest risk is stored credential echoes from supported protocol representations. The known literal scan returning zero does not prove that historical artifacts lack unseeded declared credential echoes. New filtering should be verified against a real hook output before activation.

Review the corrected registration identity semantics, source-drift handling, and how the health summary distinguishes capture loss from native execution failures. Those decisions affect later interpretation even when hook behavior is unchanged.

The independent host enforcement/context probe remains incomplete. The generated web_dist effect from the aborted bootstrap attempt needs the primary agent's recorded assessment. This report certifies the baseline defects and bounded passing tests, not the concurrent fixes, deployment of those fixes, all-hook parity, or a completed host policy matrix.
