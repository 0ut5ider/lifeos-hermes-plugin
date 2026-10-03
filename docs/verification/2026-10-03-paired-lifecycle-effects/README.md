# Paired lifecycle effect evidence

Date: 2026-10-03. Nine selected cases pass through real Claude Code and Hermes lifecycle events. These cases add effect evidence for six registrations. The [effect ledger](../../parity/handler-effects.json) now has selected paired cases for eight of 74 registrations. Complete handler effects remain open.

The reference uses Claude Code 2.1.272. Hermes uses the staged source from the [pinned compatibility manifest](../2026-10-03-hook-compatibility/source-manifest.json). This run adds no product runtime change. The [runtime manifest](runtime-manifest.json) records module resolution, native binary hash, installed plugin file hashes, and driver hashes. All 44 installed plugin Python files match the local plugin source.

## Cases and assertions

| Case | Registration | Required effect on each client |
| --- | --- | --- |
| `healer-executable` | `SessionStart.1.1` | Repair the registered script's executable permission, record the repair, and preserve the unregistered script's mode. |
| `freshness-reviewed` | `SessionStart.1.4` | Create the cache, mark reviewed TELOS as fresh, and retain consistent file counts. |
| `settings-merge` | `SessionStart.1.5` | Merge system and user values and write a snapshot equal to the generated settings. This case runs MergeSettings only. |
| `settings-backport` | `SessionStart.1.5` | Backport a direct settings edit to the user overlay before merge. Preserve the edit and write the matching snapshot. |
| `cleanup-work` | `SessionEnd.1.2` | Complete work and ISA state, remove the current session name, and preserve the unrelated session name. |
| `learning-active` | `SessionEnd.1.1` | Write exactly one learning for active synthetic work, with the real session ID and one closed claim. |
| `learning-complete` | `SessionEnd.1.1` | Write the same selected learning fields when the work already has complete state. |
| `cleanup-learning-parallel` | `SessionEnd.1.1`, `SessionEnd.1.2` | Complete cleanup and retain exactly one learning when both commands are in the same hook group. |
| `update-counts-no-oauth` | `SessionEnd.1.3` | Exit successfully without credentials and create no usage cache. This case covers only the credential-free branch. |

Each side uses a new synthetic home. A fixture hook blocks UserPromptSubmit before model generation. The real client emits SessionStart and SessionEnd. The driver requires exactly one invocation of each selected hook, the expected hook event, a consistent real session ID, successful hook exits, and a successful CLI exit. It compares the selected before and after state and requires the effect above. Equal missing effects cannot pass.

All 18 CLI runs pass. Both clients run ten selected hook invocations across the nine cases, including the two commands in the parallel case. All 20 hook invocations exit with status zero. Each native run makes no request to the loopback guard. Each Hermes run makes two `/api/show` metadata requests containing only the synthetic model name. No run makes an observed model generation request. The guard returns HTTP 401 and supplies no model response. The CLI results report zero generated tokens.

## Retained data

The [paired results](paired-results.json) retain the compared state and assertion results. Each `native/<case>/` and `hermes/<case>/` directory contains eight files:

- `result.json`: actual command, source hashes, session ID, duration, request bodies, and raw artifact hashes.
- `hooks.jsonl`: exact hook input bytes in Base64, child stdout, child stderr, exit code, and event.
- `fixture-events.jsonl`: real client event payloads.
- `cli.log`: actual CLI output for the blocked synthetic turn.
- `before-state.json` and `after-state.json`: selected state used by the assertions.
- `fixture-files-before.json` and `fixture-files-after.json`: synthetic effect files with exact bytes in Base64 and permission modes.

The [configuration](configuration.json) records both commands, source locations, and account IDs. The [run log](run.log) records all nine passing comparisons. The fixture contains no real credentials or personal memory. Raw fixture paths and random session IDs remain visible. The driver supplies only the synthetic token `PAIR_LIFECYCLE`; the request guard does not retain authentication headers.

The state comparison omits generated timestamps, random session IDs, absolute home paths, and incidental log text. The raw artifacts retain them. Assertions check session identity against the real event before they produce the compared Boolean result. The freshness comparison retains the complete cache except `generated_at`. The other cases compare the explicit fields in the table. They do not claim byte equality for every file.

## Reproduce and check

The [driver](../../../scripts/paired_lifecycle_effects.py) uses the Python standard library, installed native hooks, Bun, and both real CLIs. Prepare disposable accounts and change the paths in a copy of `configuration.json`. The output name must be new because the driver refuses to reuse a fixture home. Running as root uses the configured user and group for each CLI. Running without root requires accessible fixture paths and executable dependencies for the current user.

```bash
python3 scripts/paired_lifecycle_effects.py run /path/to/configuration.json /path/to/new-output
python3 scripts/paired_lifecycle_effects.py check docs/verification/2026-10-03-paired-lifecycle-effects/paired-results.json
python3 scripts/check_hook_evidence.py
```

The ledger check validates all retained artifact hashes, reevaluates the lifecycle assertions, and requires ledger outcomes to match the retained paired results. The unit tests reject missing repairs, lost settings edits, lost unrelated state, failed CLIs, failed hooks, wrong events, wrong invocation counts, attempted generation, and claims attached to another registration.

The [verification result](verification-results.json) records 22 passing evidence and tracing tests, plus seven passing native-handler tests without skips. The [native command](native-regression-command.json) and [native output](native-regression.log) retain that selection. The broader suite is not rerun for these evidence-tool changes. Its earlier results remain in the compatibility bundle.

## Limits

These cases select individual handlers or the learning and cleanup pair. They do not test the full installed startup or shutdown group, every scheduling order, every handler branch, or model and user delivery. The UpdateCounts case does not test an OAuth-backed refresh. The settings case does not establish atomicity under concurrent edits. The healer case does not test interpreter repair. The freshness case uses one reviewed synthetic source.

The dispatch ledger remains at 65 matched registrations and nine absent native controls. This work does not change those counts. The complete-effect gate still exits with status 1. No active profile, gateway, or deployed plugin changes on `.212`. The synthetic homes remain under each test account's `workspace/paired-effects-20261003/lifecycle-paired-v2-20261003/`. They can be removed after evidence review.
