# Hook compatibility evidence

Date: 2026-10-03. Complete hook compatibility remains unverified. The dispatch
ledger now matches 65 of 74 registrations. This bundle verifies two selected
handler effects and retains the remaining limits.

The [source manifest](source-manifest.json) pins Hermes `758ad514e` and LifeOS
`5e2f2e8`, with nine Hermes patch groups and ten LifeOS patches. The native
reference uses Claude Code `2.1.272`. The catalog fix first appears in plugin
commit `968de9d`. The candidate uses the synchronized source and runtime patches.
The active `.212` profiles still use merged plugin revision `d5dafbc`.

## Paired effects

| Registration | Native observation | Hermes observation | Limit |
| --- | --- | --- | --- |
| `PostToolUse.5.1`, ToolSearch Safety | The real search invokes Safety and emits a 249-byte notice. | The real search invokes Safety once and delivers its notice in the CLI tool-result stream. | The native session fails at its next model request because the private gateway rejects `tool_reference` content. |
| `StopFailure.1.1`, EventLogger | The interactive CLI receives HTTP 401 and writes the native failure audit row. | The one-shot CLI receives HTTP 401 and writes the same normalized audit row. | The native CLI is terminated after the event. The terminal API failure is expected. |

The [paired outcomes](paired-effects.json) contain equal hook-output and context
hashes for ToolSearch. The [selected hook outputs](toolsearch-hook-outputs.json)
retain the notice, actual search input, and response object keys. The native and
Hermes catalog algorithms return different objects. This comparison checks the
Safety effect on benign search results; it does not compare catalog algorithms
or cover every Safety branch.

The [native failure audit](native-failure-audit.json) and
[Hermes control results](hermes-control-results.json) retain the actual failure
rows. Normalization removes only `timestamp` and `session_id`. Both remaining
objects contain `event_type: stop_failure`, `hook_event: StopFailure`, and
`error_details: authentication_failed`.

The [native control results](native-control-results.json) retain commands,
environment overrides, tool inventory counts, and the observed registrations.
`ENABLE_TOOL_SEARCH=false` lists 125 tools without ToolSearch. Setting it to
`true` lists 126 tools with ToolSearch. A loopback proxy advertises a Haiku model
name and forwards to the same private LAN model. MCP search uses 100 synthetic
tools with 1,200-character descriptions and `MCP_CONNECTION_NONBLOCKING=0`.

The private traces retain exact hook input bytes and child output. Their hashes
are recorded in `paired-effects.json`. The private local copy is under
`~/.cache/lifeos-hook-evidence-20261003/`. Disposable profiles and operator files
remain under each test account's `workspace/hook-evidence-20261003/` on `.212`.
Credentials and full session transcripts are outside this public bundle.

## Measured fix

Hermes returns early for catalog tools in `handle_function_call`. That return
previously omitted result transforms and augmentation. LifeOS Safety therefore
did not receive ToolSearch results. The compatibility patch emits the observer
event, then runs the existing result transform and augmentation path.

The [regression](../../../tests/test_host_catalog_hooks.py) uses the real host
dispatcher, actual plugin registration, real deferred todo catalog, and a child
hook in a disposable profile. It fails before the fix and passes afterward. It
checks one hook invocation, the actual result payload, and context delivery to
the caller. The [before and after result](catalog-regression-results.json)
records the same regression with only the catalog fix reversed in a disposable
tree. Its [before log](catalog-before.log) fails; its [after log](catalog-after.log)
passes. The scratch source is restored. The live search confirms the real Safety
notice reaches the CLI.

## Validation

| Check | Result | Evidence |
| --- | --- | --- |
| Native handlers | 46 tests pass with no skips in 14.502 seconds against the staged source. | [Log](native-handler-gate.log), [command and environment](native-handler-command.json), [result](native-handler-result.json) |
| Patched Hermes selection | 105 tests pass. | [Log](host-gate.log), [commands](candidate-commands.json) |
| Live SSH and Docker | 19 tests pass with no selected skips. | [Log](remote-gate.log), [command](remote-command.json), [result](remote-result.json) |
| Earlier affected modules | 62 tests pass after fixture dependency and bundled patch corrections. | [Log](affected-gate.log) |
| Full plugin repeat | 1,067 tests run in 861.640 seconds: 1,047 pass and 20 skip. | [Log](full-suite.log), [result](full-suite-result.json), [command](full-suite-command.json) |
| Earlier full repeat | 1,067 tests run, with one prompt naming error and 20 skips. | [Failed run](full-suite-prompt-failure.log), [result](initial-full-result.json) |

The first broad run lacked existing `yaml` and Pulse `minisearch` fixture
dependencies. It also found a stale runtime patch copy. The prepared fixture now
uses the existing declared dependencies, and both patch copies agree. The
affected modules pass after these corrections. No package dependency is added.

The earlier full run finds no session-name file in the live-model prompt naming
test. Five isolated repeats and a repeat after full-suite imports pass. The full
instrumented repeat also passes. Its [captured output](prompt-full-trace.jsonl)
confirms inference creates the session name. The [instrumentation driver](full-suite-driver.py)
calls the real child execution method and records its completion. To reproduce
the command, use this retained driver and the environment in `candidate-commands.json`.
These passes do not explain the earlier error. The failed run remains retained,
and the cause of the intermittent naming failure is unverified.

The local full suite skips 19 remote cases and one browser case. The separate
live SSH and Docker gate covers all 19 remote cases. Browser acceptance remains
outside this evidence bundle. No passing count establishes all paired handler
effects or the complete installation and update gate.

## Remaining controls and completion gate

| Registrations | Missing native event | Measured result |
| --- | --- | --- |
| `PostToolUse.2.1` | Successful WebFetch | Domain verification rejects the public fetch, including through the constrained public proxy. |
| `PostToolUse.3.1` | Successful WebSearch | The private gateway rejects the native server-tool definition with HTTP 400 because `input_schema` is missing. |
| `PostToolUse.10.1` through `.10.7` | MultiEdit | Both tested native inventories omit MultiEdit. |

The [effect matrix](../../parity/handler-effects.md) gives all 74 registrations
an expected effect. Its [JSON ledger](../../parity/handler-effects.json) keeps
related native tests separate from selected paired cases. All complete handler
effects remain open. Two registrations have selected verified cases; 72 have no
paired effect case attached in this ledger. Historical permission comparisons
retain their separate scope in the [parity plan](../../parity-resolution-plan.md).

```sh
python scripts/check_hook_evidence.py
python scripts/check_hook_evidence.py --require-complete
```

The first command checks inventory completeness, equal recorded outcomes, and
retained artifact hashes. The second command currently exits with status 1
because complete effects are unverified. The check does not independently prove
that a case exercises every handler branch. Reviewers must inspect the cases.

## Isolation and review

The controls use disposable copies of the reference and acceptance profiles.
The active acceptance configuration, environment file, and hook settings retain
their original hashes. The work does not deploy the catalog fix to either active
`.212` installation or change `.211` or `.213`.

The [cleanup record](cleanup.json) confirms removal of the temporary SSH key
authorization, restoration of the Docker socket access control list, and stopping
the public fixture proxy. The reference account's firewall remains unchanged.
The copied profiles and raw evidence remain available for reproduction.

Review the catalog callback change and the distinction between dispatch and
complete handler effects. The patch also runs existing callbacks for other
catalog results. The pinned gateway's ToolSearch and WebSearch limitations and
the intermittent prompt naming failure remain review limits. Complete handler
effects and the installation and update gate still prevent a compatibility claim.
