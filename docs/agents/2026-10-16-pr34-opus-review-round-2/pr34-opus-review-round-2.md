# PR34 independent review, round 2

- Date: 2026-10-16
- Role: independent read-only code reviewer (review sub-agent), round 2
- Model: Claude Opus 5.5 (`claude-opus-5-5`)
- Question: Do the round 1 corrections in PR34 (https://github.com/0ut5ider/lifeos-hermes-plugin/pull/34) resolve F1 to F4 without a regression, and does the complete PR keep strict first-turn admission, admitted and Hermes-owned mirrors, and a correct native patch?
- Checkout: `/home/outsider/Projects/Hermes_agent/LifeOS_plugin`, branch `feature/discord-notification-admission`, head `3cfddbfce4d82808f0277f53b8a1f06a8be0aa72` (verified with `git rev-parse HEAD`), base `origin/main` `30b383f1`.

## Verdict

CLEAR. I found no outstanding actionable issue. All four round 1 findings are resolved, and I verified each fix independently. The observations below are optional and do not block merge or qualification.

## Round 1 findings: independent verification

| Finding | Status | Evidence |
|---|---|---|
| F1 medium: mirror purpose reused the delivery channel gate | Resolved | The four round 1 reproducers that failed at `3634f58b` now pass unchanged (`round1-rerun-summary.txt`: unbound 21 OK, DM 1 OK, lineage 3 OK). New probes below confirm the unbound path stays strict. |
| F2 low: generator omitted `gateway/mirror.py` | Resolved | `GROUPS` now owns `gateway/mirror.py` and `gateway/platforms/webhook.py` (`scripts/rebuild_hermes_patches.py:59-61`). Regeneration from the fixture produces a lifecycle patch that is byte-identical to the committed patch. The other nine differ only in `index` lines (`rebuild-compare.txt`: 0 non-index diff lines each). The trailing duplicate `gateway/mirror.py` hunk is gone. |
| F3 low: webhook mirror ran synchronous checks on the loop | Resolved | `gateway/platforms/webhook.py:949` awaits `asyncio.to_thread(self._mirror_delivery, ...)`. My synchronous-caller reproduction fails the heartbeat test with `[False] != [True]`. The patched caller passes the test five times out of five (`round2-probes.out`, `heartbeat-repeat.txt`). |
| F4 low: no real send-tool origin lookup | Resolved | `test_send_tool_resolves_real_gateway_session_before_and_after_admission` creates the row with `SessionStore.get_or_create_session` and calls the actual `_mirror_sent_message` without a session. It asserts refusal before admission and a mirror after admission. |

## F1 correction analysis (`lifeos_hook_bridge/discord_delivery.py`)

The decision order for `purpose='mirror'` in `check()` is:

1. The platform, purpose, and profile home must match. Otherwise the result is `block`. A different profile home is refused (probe `other-home decision`). Under multiplex, `get_plugin_manager()` is keyed by the resolved home, and `to_thread` copies the context. The plugin instance for that home therefore receives its own `hermes_home`.
2. If `lifeos-memory.json` is absent and is not a symlink, the result is `allow` with `mirror: True`.
3. The policy loads the configuration. A malformed, unsafe, or symlinked file raises and maps to `block`. This is a deliberate fail-closed choice, and `test_invalid_memory_configuration_still_refuses_mirrors` pins it. `load()` does not touch the LifeOS mount, so an offline mount does not cause a refusal.
4. If `ownership_enabled` is false, the result is `allow` with `mirror: True`, and no Discord request occurs (`test_returned_ownership_keeps_mirrors_when_channel_audience_changes` asserts zero requests).
5. If the destination is unbound, the result is `allow` with `mirror` equal to `_mirror_admitted`. No audience request occurs.
6. If the destination is bound, the current audience must match. Then `mirror` equals `_mirror_admitted`, which also requires the binding owner as the author.

`_mirror_admitted` requires all of the following: a stored stamp with a string `generation` for this exact session, a stored `session_id` equal to it, transport `discord`, a current account mapping from the author to the principal, destination equal to `chat_id`, private visibility, and participants equal to the principal alone. It also requires a scope signature equal to the stored one. `MemoryPolicy.resolve` includes `self.revision` (a SHA-256 of the complete configuration) in the signature (`memory_policy.py:101-104`). Any configuration edit therefore refuses the mirror, and the next `admit` also refuses. The mirror and admission decisions change together.

Probe results (`round2-probes.out`, `test_review_round2.py`):

| Probe | Decision | Mirror |
|---|---|---|
| Admitted DM, owner account mapping removed | `allow`, `mirror: False` | refused, empty transcript |
| Admitted DM, `discord:70` grant revoked | `block` (`MemoryAdmissionError` is a `RuntimeError`, caught) | refused |
| Second unadmitted DM session, same destination | refused | empty transcript |
| DM-admitted session mirrored to bound channel `60` | `allow`, `mirror: False` | refused |
| State file mode `0644` | `block` | refused |
| Different profile home | `block` | refused |
| Channel `60` admitted while bound, then binding removed | `allow`, `mirror: False`, zero Discord requests | refused. The next `admit` also refuses ("visibility is unknown") |
| Synchronous webhook caller (pre-fix reproduction) | heartbeat `[False]` | as round 1 described |

Delivery purpose is unchanged. The only new delivery-path behavior is the explicit `purpose not in ('delivery', 'mirror')` refusal. The native delivery caller does not pass a purpose and receives the default `'delivery'`.

## Other areas checked with no finding

- Notification before the first human prompt: `mirror_to_session` resolves the session (explicit or origin lookup) before it calls the policy. It refuses before `_append_to_sqlite`, so history stays empty and `is_first_turn=True` is preserved. The policy never writes state, so no notification creates an admission (`test_notification_does_not_create_an_admission`). The cron `_seed_cron_session` path creates an empty row and its mirror is refused. The first human turn in that row is still a first turn.
- Native call sites: `send_message_tool._handle_send` is synchronous and runs in the tool worker. The cron ticker runs in its own thread (`cron/scheduler_provider.py`, "ticker thread"). The webhook call site is now off the loop. I found no other `mirror_to_session` caller in production code.
- Context and secrets in the worker thread: `_HERMES_HOME_OVERRIDE` and `_SECRET_SCOPE` are `ContextVar` objects, and `asyncio.to_thread` copies the context. The PR heartbeat test sets the secret scope on the loop thread, and the bound-channel audience lookup succeeds from the worker. This proves that the token reaches the worker.
- Concurrency: `PrivateDiscordDelivery.check` keeps no shared mutable state. It builds `MemoryRuntime` per call, and `_states()` reads an atomically published file. A stale read only refuses a mirror, which is the safe direction. Configuration reloads before each return detect a concurrent edit.
- Exceptions and resources: every policy failure maps to `block`. `HTTPError` responses are closed before re-raise (`discord_audience.py:58-63`). The suite runs under `-W error::ResourceWarning` with no warning.
- Lineage: compression children created by `rotate_session` keep the mirror. A reset successor refuses until its first admission (`round1-rerun-test_review_lineage_mirror.out`).
- Patch integration: all ten Hermes patches apply with `git apply --whitespace=error-all` to the stock archive (sha256 `216eaa0a...`, same as round 1). All 95 patched paths are byte-identical to the fixture (`replay-vs-fixture.txt`). The `index` abbreviation change in the lifecycle patch (9 to 8 hex digits) does not affect `git apply`, and replay proves it.
- Webhook cancellation: the new `await` after a successful send adds a cancellation point. `_send_with_retry` retries only on a failed `SendResult`, not on exceptions. The delivery ledger already treats a crash during `attempting` as at-least-once with a visible recovered marker, and `base.py` already awaits `to_thread(mark_delivered, ...)` after the send. This adds no new class of duplicate.
- Release metadata: `VERSION` and all four manifests read `0.7.1`, and `test_release_version` passes. The `PROGRESS.json` `source_sha256` values match the head files (`source-sha256.txt`).

## Observations (optional, not blocking)

1. Dead branch: `_mirror_admitted` starts with `if not configuration.get('ownership_enabled', False): return True` (`discord_delivery.py:17-18`). Both callers now return before that branch when ownership is off, so the branch cannot run. Removing it changes no behavior. Keeping it is harmless.
2. Silent policy refusal: the native mirror returns `False` with no log when the policy refuses (`gateway/mirror.py`, patched lines 66-77). The cron caller then logs at debug level "no matching gateway session" with a "cold start" label, which misnames the cause. An expected pre-admission refusal makes this the common case on daily. If later diagnosis of a missing transcript line matters, a debug log in the refusal branch would help. Adding it would touch the native patch again.
3. `TODO.md` has two open items that describe the same remaining work ("Review, qualify, and deploy the notification admission fix" and "Complete PR34 Opus 5.5 review, exact 0.7.1 package qualification ..."). This is documentation tidiness only.
4. Carried from round 1 and still true: `gateway/mirror.py` uses `has_hook` without lazy discovery. I found no reachable bypass on a restricted profile. `_RefuseRedirects` leaves a 3xx response open until garbage collection. That code predates PR34.

## Test runs

Environment (cwd repository, `H=/home/outsider/.cache/lifeos-discord-admission-20261016/hermes`):

```
LIFEOS_HERMES_SOURCE=$H LIFEOS_HERMES_REBUILD_SOURCE=$H \
LIFEOS_MEMORY_SOURCE=/home/outsider/.cache/lifeos-discord-admission-20261016/native-source \
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=.:tests:$H \
/home/outsider/.cache/lifeos-daily-promotion-20261014/frozen-test-environment/bin/python -W error::ResourceWarning -m unittest -v \
  test_discord_notification_mirror test_discord_audience test_discord_private_delivery test_memory_runtime \
  test_memory_compression test_memory_rotation test_memory_history test_daily_morning_delivery \
  test_hermes_patch_regeneration test_release_version
```

| Run | Result | Files |
|---|---|---|
| Focused bridge suite | `Ran 138 tests ... OK`, exit 0. Stderr has only three asyncio slow-callback diagnostics (0.27 to 0.34 s) in `test_discord_private_delivery`, the same class as round 1. No skips, warnings, or tracebacks. | `bridge-suite.*` |
| Native pytest (cwd `$H`, absolute repository paths on `PYTHONPATH`, `-p no:cacheprovider`): mirror, cron origin fallback, send tool, all webhook modules | `177 passed in 27.79s` | `native-pytest.out` |
| Round 1 reproducers rerun (round 1 directory on `PYTHONPATH`) | 21 + 1 + 3 OK | `round1-rerun-*` |
| Round 2 probes | 8 OK, with printed decisions | `round2-probes.out`, `test_review_round2.py` |
| Heartbeat test repeated | 5 of 5 OK | `heartbeat-repeat.txt` |
| Patch replay on stock archive | 10 of 10 exit 0, 95 of 95 paths equal the fixture | `independent-replay.txt`, `replay-vs-fixture.txt` |
| Regeneration to a temp directory | lifecycle identical, others differ only in `index` lines | `rebuild-compare.txt` |

The shared fixture's `git status --short` list is identical before and after all runs (95 entries, `hermes-status-before*.txt`). Replay and rebuild outputs went to temp directories under `/tmp`, which I removed.

## Files in this directory

- `prod.diff`: production, patch, and release-metadata diff `origin/main...HEAD`. `round2-fix.diff`: `3634f58b..3cfddbfc` for bridge code, patches, scripts, and tests. Both files are raw captures and keep the verbatim trailing whitespace of patch context lines.
- `bridge-suite.stdout`, `bridge-suite.stderr`, `bridge-suite.exit`, `native-pytest.out`: test runs.
- `independent-replay.txt`, `replay-vs-fixture.txt`, `rebuild-compare.txt`: patch checks.
- `round1-rerun-summary.txt`, `round1-rerun-*.out`: round 1 reproducers at the new head.
- `test_review_round2.py`, `round2-probes.out`, `heartbeat-repeat.txt`: round 2 probes. They use synthetic fixtures only and write only to temp directories that the fixtures create.
- `source-sha256.txt`, `hermes-status-before.txt`, `hermes-status-before-files.txt`: integrity records.

I did not edit source, commit, push, merge, contact servers, delegate, or use memory or journal tools.
