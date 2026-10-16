# PR34 independent review, round 1

- Date: 2026-10-16
- Role: independent read-only code reviewer (review sub-agent)
- Model: Claude Opus 5.5 (`claude-opus-5-5`)
- Question: Does PR34 (https://github.com/0ut5ider/lifeos-hermes-plugin/pull/34) keep strict memory admission for the first human Discord prompt after an automatic notification, keep admitted and Hermes-owned mirrors working, and integrate its native Hermes patch correctly?
- Checkout: `/home/outsider/Projects/Hermes_agent/LifeOS_plugin`, branch `feature/discord-notification-admission`, head `3634f58b3b57e8af031278d532734b11225ce477` (verified), base `origin/main` `30b383f1`.

## Verdict

NOT CLEAR. The incident fix works: one medium finding, two low findings, one low test-coverage finding.

The core incident path is correct. A notice sent through the actual `send_message_tool` mirror path (origin lookup, no explicit session) is refused for an unadmitted foreground session. History stays empty, and the first human turn admits with `is_first_turn=True`. Admitted sessions, compression children created by `rotate_session`, and reset successors after their first admitted turn all keep mirrors. Revoked scope, changed audience, a foreign author, and a different session are all refused. No notification creates an admission.

## Findings (most severe first)

### F1. Medium. Mirror purpose inherits the delivery channel gate and refuses mirrors that LifeOS does not govern

- File: `lifeos_hook_bridge/discord_delivery.py:46-61` (binding and audience gate run before `_mirror_admitted`). The native patch adds the trigger at `lifeos_hook_bridge/patches/hermes-session-lifecycle.patch:1772-1784` (`gateway/mirror.py` lines 66-77 after application).
- Cause: `check(purpose='mirror')` returns `denied` (`action: block`) when the configuration is missing, when `chat_id` is not in `discord_channels`, or when the channel audience is not private. This happens before the `ownership_enabled` short circuit in `_mirror_admitted`. The native mirror treats `block` as "skip the transcript write".
- Why it is a regression: Hermes calls the delivery gate (`authorize_delivery`) only when `DISCORD_GUILD_CHANNEL_ONLY` is active (`plugins/platforms/discord/adapter_channel_policy.py:27-35, 56-65`). The new mirror gate runs for every Discord mirror whenever the LifeOS hook is registered, and `lifeos_hook_bridge/__init__.py:35-38` always registers it on a patched host. On a profile without the guild-channel restriction, delivery to a DM, thread, or other channel still succeeds. Before PR34, that profile also mirrored the message. After PR34, it silently drops the mirror.
- Measured triggers (synthetic, actual native mirror and session store, fixture Hermes):
  1. Ownership returned to Hermes (`ownership_enabled: false`), destination `999` not bound: policy returns `{'action': 'block', ...}`, `mirror_to_session` returns `False`, transcript stays empty (`unbound-mirror.out`).
  2. `lifeos-memory.json` absent: same refusal (`unbound-mirror.out`).
  3. Ownership returned, bound channel `60` now shared with a second reader: mirror refused (`unbound-mirror.out`). Delivery is also refused on a restricted profile, so this case matters only on an unrestricted profile.
  4. Ownership enabled, Discord DM grant `discord:70` with no `discord_channels` key. The configuration validates, and `MemoryRuntime.admit` admits the DM session (`visibility='private'`). The mirror into that admitted conversation is refused (`dm-mirror.out`). This breaks the requirement that admitted conversation mirrors keep working. `context_audience_is_current` (`discord_audience.py:175-177`) explicitly accepts configurations without `discord_channels`, so this configuration is not invalid.
- Scope limit: the daily `.253` profile is restricted to one bound private channel. On that profile, delivery to any other destination is already refused, so F1 does not change its observable behavior. I did not verify whether development `.252` sets `DISCORD_GUILD_CHANNEL_ONLY`. If it does not, the LifeOS plugin there now drops mirrors for every unbound Discord destination.
- The evidence README sentence "Native mirroring stays available ... after memory ownership returns to Hermes" (`docs/verification/2026-10-16-discord-admission/README.md`) is true only for a bound channel whose audience is still private.
- Smallest remedy: decide `purpose == 'mirror'` from admission state, not from the delivery gate:
  1. If the configuration is absent or `ownership_enabled` is false, return `{'action': 'allow', 'mirror': True}`.
  2. If ownership is enabled and `chat_id` is a bound channel, keep the current audience check plus `_mirror_admitted`.
  3. If ownership is enabled and `chat_id` is not bound, return `mirror` equal to the stored-admission match: same session, `transport == 'discord'`, `destination == chat_id`, private visibility, owner participants, and a current scope signature. Do not require a channel binding.
  Add regression cases for triggers 1, 2, and 4. The review files `test_review_unbound_mirror.py` and `test_review_dm_mirror.py` assert the expected `True` and fail today.

### F2. Low. Patch generator does not own `gateway/mirror.py`; the native fix is hand-appended

- File: `scripts/rebuild_hermes_patches.py:59-83` (`hermes-session-lifecycle.patch` group). Patch text: `lifeos_hook_bridge/patches/hermes-session-lifecycle.patch:1760-1788`.
- Cause: The mirror hunk is appended by hand. It has a blank separator line and no `index` line, unlike every generated section. `GROUPS` does not list `gateway/mirror.py`.
- Measured: against the fixture Hermes tree (HEAD `71d34bad`, the supported commit), `changed - assigned == ['gateway/mirror.py']` (`rebuild-unassigned.txt`). `rebuild()` therefore raises `Patch assignment differs` for any prepared source that contains the fix. A source that lacks the fix, such as the default `LIFEOS_HERMES_REBUILD_SOURCE` from 2026-10-05, regenerates `hermes-session-lifecycle.patch` without the mirror hunk. `test_hermes_patch_regeneration.py` would still pass, so the next regeneration can drop the fix without any error.
- Smallest remedy: add `'gateway/mirror.py'` to the `hermes-session-lifecycle.patch` group. Then regenerate the bundle from a prepared source that contains the fix, and confirm byte equality with the committed patch (or accept the generated form).

### F3. Low. Webhook mirror now runs synchronous Discord REST audience checks on the gateway event loop

- File: native call site `gateway/platforms/webhook.py:947` (inside `async def _deliver_cross_platform`) calls the synchronous `mirror_to_session`. The patched `gateway/mirror.py:70` calls synchronous `invoke_hook`, and `discord_delivery.py:53` performs blocking `urllib` requests.
- Measured: one mirror decision makes 5 Discord REST requests (`/users/@me`, `/channels/60`, `/guilds/10`, `/guilds/10/roles`, `/guilds/10/members?limit=1000`) on the calling thread (`mirror-requests.out`). Each request has a 3 second timeout, and the required-hook bound is 30 seconds. Before PR34, this mirror was one SQLite append. The delivery gate avoids this by using `ainvoke_hook`, which moves required hooks to a worker thread.
- Trigger: a webhook route with `mirror_to_session: true` that delivers to Discord. The route option is off by default, which is why I rate this Low. I did not measure event-loop stall time against a slow Discord API.
- Smallest remedy: accept the risk and document it, or keep the native mirror policy off the loop. For example, the webhook caller can run `_mirror_delivery` through `asyncio.to_thread`. That change adds one more native line to the same patch group.

### F4. Low (test coverage). Regression tests do not exercise the incident caller's session resolution

- File: `tests/test_discord_notification_mirror.py:69-71` and `:137-150`.
- Cause: Every test passes an explicit `session_id` to `mirror_to_session`. The incident path is `hermes send` -> `send_message_tool._mirror_sent_message` -> `mirror_to_session` without `session_id`, followed by `_find_session_id` origin lookup. The fixture's `db.create_session(...)` rows have no gateway origin, so `_find_session_id('discord', '60')` returns `None` on them (`find-session.out`). A test that calls the send tool against those rows passes for the wrong reason.
- Measured: with a real gateway row from `SessionStore.get_or_create_session(SessionSource(...))`, `_mirror_sent_message` refuses before admission and mirrors after admission (`lineage-mirror.out`). So the product behavior is correct. Only the coverage is missing.
- Smallest remedy: add the `SendToolMirrorReview` case from `test_review_lineage_mirror.py`. It creates the session through `get_or_create_session` and asserts both outcomes.

## Verified claims

| Claim | Result | Evidence |
|---|---|---|
| Head is `3634f58b` | Confirmed | `git rev-parse HEAD` |
| Focused bridge suite: 118 cases | Confirmed: `Ran 118 tests ... OK`, exit 0. Stderr contains only three asyncio slow-callback diagnostics (0.24 to 0.26 s), with no warnings, errors, or tracebacks. | `bridge-suite.stderr`, `bridge-suite.exit` |
| Native pytest: 70 passed | Confirmed: `70 passed in 19.53s`. Run with `-p no:cacheprovider`. The fixture's `git status` count is unchanged (94 before and after). | `native-pytest.out`, `hermes-status-before.txt` |
| All 10 Hermes patches replay on stock 0.7.0 archive | Confirmed independently in a fresh temp dir from PR head patches. All exit 0. Archive sha256 `216eaa0a...`. | `independent-replay.txt` |
| Fixture `mirror.py` equals patch application | Confirmed: both sha256 `b8c250ac...195c2c` | `independent-replay.txt`, `sha256sum` |
| First human turn after notice keeps strict admission | Confirmed through direct mirror (PR test) and through the actual send-tool path with a real gateway row | `lineage-mirror.out` |
| Compression child keeps mirror | Confirmed after `rotate_session` | `lineage-mirror.out` |
| Reset successor refuses until its first admission, then mirrors | Confirmed | `lineage-mirror.out` |
| HTTPError response closed | Confirmed by PR test under `-W error::ResourceWarning` | bridge suite |

## Areas checked with no finding

- Scope comparison with `replace(context, session_id='')` matches `MemoryRuntime._stamp`, which computes the stored `scope` the same way. The exact stored context separately binds the session, transport, author, destination, visibility, and participants.
- Stale fact generation (`proposal_generation` or `rendered` changed): the mirror is allowed, but the session already has history, and the next `admit` refuses it for an independent reason. The mirror does not cause that refusal.
- Races: a stale "not admitted" read only drops a mirror, which is the safe direction. A configuration change during the decision is caught by the reload comparisons at `discord_delivery.py:55` and `:59`. The state file is published atomically, so the lock-free `_states()` read is consistent.
- Exceptions: every callback failure maps to `denied`. A raising or timed-out hook becomes a `block` directive (`plugins_dispatch.py`), and the native mirror skips the write and never raises.
- Multiple decisions: the native predicate requires every decision to be `allow` and any present `mirror` key to be `True`. Python precedence of `A or B or C and D` is correct.
- `hermes_cli.config.get_hermes_home` is the same function as `hermes_constants.get_hermes_home`, which the delivery gate uses.
- Thread sessions cannot be admitted (`destination` becomes `chat/thread`, which fails the audience check), so the `destination != chat_id` comparison loses no admitted thread mirror.

## Observations (not actionable findings)

- `gateway/mirror.py` uses `get_plugin_manager().has_hook(...)`, which does not run lazy discovery. A process that never discovered plugins mirrors without policy. On a restricted profile this cannot happen, because delivery through `authorize_delivery` also needs the registered hook and refuses first. `send_message_tool.prepare_send_message_platforms` and cron call `discover_plugins()`. I found no reachable bypass.
- `_RefuseRedirects.redirect_request` raises before urllib closes the 3xx response. The response is still open when the refusal propagates (`redirect-close-probe.out`). No `ResourceWarning` appeared after GC in my probe. This code predates PR34 and is outside the PR change, but it is the same class of leak that PR34 fixes for `HTTPError`.
- Activation edge, by design: while ownership is returned to Hermes, mirrors land in fresh sessions. After re-activation, such a session needs `/new`, as any session with Hermes-era history does.

## Reproduction

Common environment (cwd `/home/outsider/Projects/Hermes_agent/LifeOS_plugin`, `R=docs/agents/2026-10-16-pr34-opus-review-round-1`):

```
LIFEOS_HERMES_SOURCE=/home/outsider/.cache/lifeos-discord-admission-20261016/hermes \
LIFEOS_MEMORY_SOURCE=/home/outsider/.cache/lifeos-discord-admission-20261016/native-source \
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=.:tests:$R:/home/outsider/.cache/lifeos-discord-admission-20261016/hermes \
/home/outsider/.cache/lifeos-daily-promotion-20261014/frozen-test-environment/bin/python -W error::ResourceWarning -m unittest -v <module>
```

| Module | Purpose | Result today |
|---|---|---|
| `test_review_unbound_mirror` | F1 triggers 1 to 3 (also reruns the 11 PR cases, which pass) | 3 FAIL |
| `test_review_dm_mirror` | F1 trigger 4, admitted DM | 1 FAIL |
| `test_review_lineage_mirror` | compression child, reset successor, send-tool path | 3 OK |
| `test_review_find_session` | F4 fixture origin lookup diagnostic | prints `None` |
| `test_review_mirror_requests` | F3 request count | 5 requests |

Other commands:
- F2: `rebuild-unassigned.txt` (computes `changed - assigned` against the fixture tree; read-only) and `rebuild-generator.txt` (`rebuild()` output, output dir was a temp dir).
- Patch replay: `independent-replay.txt` (temp dir `/tmp/pr34-replay-*`, removed afterwards).
- Redirect probe: `python -X dev redirect_close_probe.py`, output in `redirect-close-probe.out`.

## Files in this directory

- `prod.diff`: production and patch diff `origin/main...HEAD`.
- `bridge-suite.stdout`, `bridge-suite.stderr`, `bridge-suite.exit`: focused bridge suite.
- `native-pytest.out`, `hermes-status-before.txt`: native pytest run and fixture dirty-file count.
- `independent-replay.txt`, `rebuild-generator.txt`, `rebuild-unassigned.txt`: patch checks.
- `unbound-mirror.out`, `dm-mirror.out`, `lineage-mirror.out`, `find-session.out`, `mirror-requests.out`, `redirect-close-probe.out`: probe outputs.
- `test_review_*.py`, `redirect_close_probe.py`: synthetic review tests and probes. They use no personal data. They import the shared fixtures read-only and write only to temp dirs created by the fixtures.

I did not edit source, commit, push, contact servers, or use memory or journal tools. The shared native fixtures were not modified: the fixture `git status` count is unchanged, and pytest ran without a cache.
