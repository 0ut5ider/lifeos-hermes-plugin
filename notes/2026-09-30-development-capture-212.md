# Private development capture on .212

Date: 2026-09-30

## Reviewed update on the same day

Recorder commit `d7758db` replaces the initial observer after repeated independent reviews and corrections. All 29 development tests pass locally and in an isolated `.212` environment. The [review correction record](2026-09-30-logging-review-fixes.md) lists the fixes, final clear review, restart failure, launcher recovery, and backups.

The [final verification snapshot](../docs/verification/2026-09-30-reviewed-capture/verified.json) confirms stable gateway and dashboard processes, matching running recorder manifests, unchanged native source fingerprints, and protected dashboard access. Its 1,236 events have zero reported losses, gaps, integrity issues, and incomplete invocations. Registration counts represent historical versions. The observations below describe the initial 11-test deployment, including its live model, SSH, Docker, and Discord fixtures. They are not new live tests of the corrected revision.

## Initial outcome

The external development recorder is installed and active for the `lifeos-hermes` account on `192.168.8.212`. The gateway and dashboard loaded the final recorder source manifest after restart. The dashboard still returns HTTP 401 for an unauthenticated API request. All nine inspected Hermes and plugin source fingerprints remain unchanged.

The recorder observes Hermes lifecycle callbacks, bridge translation, actual hook selection and skips, command and HTTP results, detached local and remote execution, parsed decisions, host tool boundaries, model context construction, and Discord admission and delivery. It retains full ordinary content in compressed artifacts and filters recognized credentials before hashing. Span, invocation, registration, process, session, and Discord message IDs support later correlation.

The public installer still installs only `lifeos_hook_bridge/`. The development observer, Python startup file, and captured data are outside that directory. No runtime code on `.211` or `.213` changed. No push was performed for this work.

## Verification

| Check | Result | Scope |
| --- | --- | --- |
| Development tests, local | 11 passed, 4.123 seconds | Real hook subprocesses, HTTP server, disk failure, redaction, identity and thread propagation |
| Development tests, .212 | 11 passed, 3.823 seconds | Final observer source under the deployed managed Python interpreter |
| Native bridge characterization | 6 passed, 0.814 seconds | PreToolUse denial, Stop block, plaintext handling, detached context, environment and working directory |
| Live systemd detached hook | Passed | Actual launch, parent exit, child completion, discarded stderr, persisted context |
| Live SSH detached success and failure | Both passed | Real loopback SSH transport; expected missing-workdir failure recorded |
| Live Docker detached success and failure | Both passed | Real container transport; expected missing-workdir failure recorded |
| Live Hermes model and tool turn | Passed | Local model invoked terminal, committed its result, and answered `CAPTURE-TOOL-READY`; exit code 0 |
| Live Discord channel admission and reply | Passed | Plain message accepted without an @ mention; reply delivered inline |
| Final capture health snapshot | Passed | 1,179 events, zero incomplete invocations, zero capture gaps, zero artifact integrity issues |

The live model turn took 29.625 seconds. This is an observed duration, not a traced versus untraced benchmark. The SSH and Docker fixtures called the execution boundary directly. They do not prove trusted project selection or every remote tool behavior. Their temporary key, authorized-key entry, known-host changes, workspace, container, and Docker socket access were removed or restored after verification.

The inventory contains all 74 native registrations and one synthetic systemd registration. At the coverage snapshot, 36 native registrations were exercised and 38 were unexercised. An unexercised registration is not a failure. Each requires its trigger and an appropriate test. A successful completion is execution evidence, not proof that its intended file, memory, permission, or notification effect occurred.

The second-opinion review found response-classification, encoded credential, callback identity, and parser correlation problems. The primary agent fixed them and reran the tests. The review's final JSON-string credential finding is preserved at its historical snapshot. The final 11-test suite separately verifies that finding's resolution, including JSON stdin, JSON stdout, partial fragments, camelCase credential fields, and repeated declared credentials. See the [review report](../docs/agents/2026-09-30-capture-design-review/capture-implementation-review.md).

## Discord routing

The `.212` bot now uses `#hermes-212`, channel `1554859357374513222`, in guild `1553540018302099486`. Its server-channel allowlist and free-response channel both name that channel. Its user allowlist remains `708089927468056648`. `DISCORD_REQUIRE_MENTION=true` remains set, and the designated free-response channel permits ordinary messages. Replies stay inline. The proactive home channel also names `#hermes-212`.

The gateway accepted message `1554865153172963380` at 14:39:00 UTC and delivered reply `1554865270085128274` at 14:39:28 UTC. The event stream records admission, 23 hook starts and completions, model context construction, Stop gate processing, and delivery under the originating message ID. These records identify session `20260930_103901_450e7f96`. The [Discord reply](https://discord.com/channels/1553540018302099486/1554859357374513222/1554865270085128274) is the live delivery evidence. Earlier messages in `#general` selected the same-named role, which Hermes correctly ignored.

After the final restart, `gateway.log` records `Connected as Shiny Hermes Bot#3996` at 10:53:57 Toronto time. Both service processes have the final recorder source manifest. The [machine-readable verification snapshot](../docs/verification/2026-09-30-development-capture/summary.json) contains selected counts and identities, with no captured prompts or response bodies.

The routing backup is `/home/lifeos-hermes/.hermes/.env.before-discord-channel-20260930T142104Z`. The `.213` configuration was not changed. Explicit destinations in existing scheduled jobs were not rewritten.

## Private evidence and review

Account paths:

- Observer source: `~/workspace/development-hook-capture/development`.
- Configuration: `~/.config/lifeos-development-capture/config.json`, mode 0600.
- Capture root: `~/.local/state/lifeos-development-capture`, mode 0700.
- Run: `development-20260930T140347Z`.
- Startup file: `~/.hermes/tools/python-3.14.7+20260901-linux-x64/lib/python3.14/site-packages/lifeos_development_capture.pth`.

Run analysis as `lifeos-hermes` with the managed base Python interpreter. The startup file makes the recorder package available:

```sh
~/.hermes/tools/python-3.14.7+20260901-linux-x64/bin/python3 \
  -m hook_capture.analysis ~/.local/state/lifeos-development-capture
```

Start with integrity errors, capture gaps, incomplete invocations, and unexpected failures. Filter by UTC interval, session, registration, or invocation. Expand only the artifacts needed to inspect a suspected pattern. Native interventions and deliberately failed probes must remain distinct from unexpected failures. The [development guide](../development/README.md) gives the filters and artifact layout.

No recurring review job or automatic deletion is configured. The directory contained about 4.7 MB at the first live conversation snapshot. Monitor growth during regular use. Raw prompts, transcripts, hook output, and captured model context remain private. Public reports should contain counts and verified findings, not raw conversation artifacts.

## Limits and undo

The observer reads only inspected boundaries. It does not prove all 74 hooks have equivalent semantics, inspect arbitrary unknown Python objects, download attachments solely for tracing, or read beyond the native HTTP limit. Unknown credentials in free-form prose or unrelated encodings can still escape recognition. Instrumentation overhead has not been measured comparatively. Source updates require inspection and capture fingerprint refresh.

To disable capture for subsequent processes, run the managed Python interpreter with `-m hook_capture.setup disable`. Use `remove` to also remove the Python startup file. Restart `hermes-gateway.service` and `hermes-dashboard.service` after active turns finish. Existing evidence remains available. The external source and private configuration can remain for later development use.

To undo Discord routing, restore the named private `.env` backup and restart the gateway. This also restores the earlier home channel and mention rules. Do not restore that file after unrelated credential changes without reviewing which keys it would replace.

Broader hook parity and the deferred memory integration remain separate work. This logging deployment provides evidence for that work; it does not close the parity release gate.
