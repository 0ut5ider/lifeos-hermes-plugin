# Isolated LifeOS test environment

As of 2026-10-03, the development fixture is the unprivileged `lifeos-hermes` account on `192.168.8.212`. It started with fresh Hermes and LifeOS installations. No LifeOS data was copied from an existing installation. The principal is the fictional `Test Operator`.

The [merged release record](verification/2026-10-03-merged-release-212/README.md) covers this Discord fixture and the separate `lifeos-plugin-install-probe` browser profile. Both active installations now run plugin version `0.1.0` at merged commit `d5dafbcac41434eb9aac2c4c7880a9b9be8135a4`. The release preserves existing profiles and keeps memory ownership disabled.

## Installed baseline

- Hermes v0.21.5 at local commit `6056259cc67cb6daeaf8d6ceffabbc524598e418`, built from base `758ad514` and nine reviewed patch groups. The account has a local model, a LAN dashboard, and a separate Discord test bot. Required middleware protects model execution and admission. The command denial patch makes an explicit native denial block a recoverable approval. The Stop gate withholds rejected answers. Its default continuation limit matches Claude Code; the plugin can select a failed turn at that limit. Iteration-budget exhaustion fails the turn.
- LifeOS at base commit `5e2f2e8`, with all ten compatibility patches installed into `~/.hermes`. The current prepared source is `~/workspace/releases/20261003-merged-d5dafbc/prepared/lifeos/LifeOS/install`. The old `~/workspace/LifeOS` checkout remains available for reference. The merged release includes the required memory checks and preserves the native hook settings.
- The installed bridge is pinned to public plugin commit `d5dafbcac41434eb9aac2c4c7880a9b9be8135a4`. Its VersionDrift baseline covers 1,798 files and reports zero changes at final release verification. Pulse runtime state is excluded from drift checks. Later generated architecture timestamps can create new drift.
- A fresh personal tree from `ScaffoldUser.ts --config-root ~/.hermes --apply`, linked by `LinkUser.ts --config-root ~/.hermes --apply`.
- LifeOS's shipped Hermes sidecar mount, including its identity renderer and guard plugin.
- LifeOS's 74 native Claude Code hook registrations installed in the test account, plus the separate `lifeos-hook-bridge` Hermes plugin.
- Bun 1.4.2 and ripgrep 15.2.0.
- The Hermes main loop uses xhigh effort, matching the configured Fable tier. A native IntegrityCheck test passed the Hermes carrier and model-rung sections after this change. The previous medium setting produced a main-rung mismatch.
- The four LifeOS tiers use Hermes's `custom` provider and `flashnext-w4a16-fp8ple`. Haiku uses low effort, Sonnet uses medium, and Opus and Fable use xhigh. Native LifeOS inference uses the plugin-owned `hermes lifeos-infer` command and Hermes provider routing. Claude Code remains installed for reference tests.
- The Discord extra is installed through `hermes pm install --extra discord`. The `hermes-gateway.service` user service is enabled, and systemd linger keeps it running after logout.
- The Discord gateway now accepts Adrian's ordinary messages in `#hermes-212`, channel `1554859357374513222`, without an @ mention. Its server-channel allowlist restricts it to that channel and its threads. The user allowlist remains active. Replies are inline, and the same channel is the proactive default. The `.213` gateway configuration remains unchanged.
- Hermes's `agent-browser` and `chromium` packages are installed through `hermes pm install agent-browser chromium` for local browser hook tests.
- LifeOS Pulse runs as the `com.lifeos.pulse` user service on loopback port 31337. Its five enabled template jobs are overridden to disabled in `LIFEOS/USER/CONFIG/PULSE.user.toml` for this test account. The service provides the local Skill and Agent HTTP hook routes.

The installer detects Hermes, but its deployment tools default to `~/.claude`. Pass `--config-root ~/.hermes` explicitly. One runtime generator still writes to `~/.claude`, and many shipped files refer to that path. The fixture uses `~/.claude` as a link to `~/.hermes` until the path behavior has been mapped and addressed. This link is a test workaround, not a portable plugin installation method.

Hermes's stock `research` skill collides with LifeOS's `Research` skill in the LifeOS installer's case-insensitive collision check. The fixture backs up the stock skill outside Hermes's skills directory and installs the LifeOS skill. A distributable installer needs a deliberate policy for this collision.

Identity substitution also replaces placeholder literals in LifeOS's installed `InstallEngine.ts`. The fixture restores that file from the public release after substitution. This is an upstream installer issue to account for in automated setup.

## Verified behavior

- `Mount.ts --check` reports that the identity file and config are current.
- A live Hermes CLI turn answers `Test Operator` when asked for the principal name.
- The mounted guard passes its 61 shipped policy tests.
- The dashboard remains active and rejects an unauthenticated API request with HTTP 401.
- LifeOS Doctor reports identity rendering and filesystem search live.
- The Pulse Skill guard blocks its known false trigger through the bridge. The Pulse Agent guard returns foreground advice through the bridge. The background flag maps from Hermes's top-level delegation context, and a child delegation maps to foreground.
- A disposable SSH target demonstrated that Hermes now refuses a whole-file write when a remote ISA changes after it was read. A fresh read permits a merged write. The target account and key were removed after testing.
- A native Bun probe with a backend digest recorded an ISA view for a path absent on the host, blocked a changed digest, and allowed a fresh read. A local ISA still blocked a stale write. The bridge test confirmed that a model-supplied digest cannot replace the backend digest.
- A second disposable SSH target exercised Hermes `read_file_tool`, the bridge, and native `PreToolGuard` together. An external edit triggered the native stale write block; a fresh read cleared it. The target account and key were removed.
- User hooks run for a remote tool workdir that is absent on the Hermes host. Synchronous and asynchronous child processes start from the local LifeOS root while the hook payload retains the remote `cwd`. A same-path trusted host project hook is excluded for a remote backend. The installed Hermes backend classifier identified the active SSH class under its resolved `default` task key.
- A disposable SSH project on `.212` accepted trusted project command and loopback HTTP hooks. An exit-code-2 command blocked a tool call. The bridge rejected missing trust, the wrong endpoint, unsafe trust-file permissions, and a workspace symlink that escaped the trusted root. Remote settings and skill edits reached `ConfigChange`; an asynchronous hook returned context after its parent process exited. The project used synthetic hook commands and no LifeOS data.
- A disposable Docker project on `.212` accepted a hook only when its trust entry named the running container's immutable image ID and project root. The command blocked a tool call. Project settings and skill edits reached `ConfigChange`, a container-local HTTP hook denied a tool call, and a detached async hook returned context after its parent exited. The test account received temporary access to the Docker socket for this probe; the access entry and probe containers were removed.
- A second disposable Docker container exercised Hermes `read_file_tool`, the bridge, and LifeOS's native ISA guard. An external edit caused a stale whole-file Write block. A fresh read cleared the block. The container and temporary Docker socket access were removed after the test.
- Disposable Docker and loopback SSH workspaces each ran an inner `read_file` through Hermes `execute_code`. The LifeOS transcript recorded `Read` under the outer session in both cases.
- The separate `.212` Discord bot sent an outbound test to `#general`. An unmentioned channel message was ignored under Hermes's default mention rule. Adrian mentioned the bot; the gateway admitted the message, created a thread, and sent a `READY-212` reply there. A one-time scheduled script job also delivered a marker to `#general` after the cron worker bootstrap fix. See the [Discord setup guide](discord-setup.md).
- A 127-second background delegation in the bot thread triggered a native LifeOS watchdog signal. Hermes injected it into the Discord session, and the bot posted an alert followed by `WATCHDOG-212-DONE`. The watchdog classified the deliberate wait as silence. See the [live watchdog record](../notes/2026-09-28-live-watchdog-background.md).
- A local Chromium session fetched a disposable loopback page. Its full browser snapshot contained an instruction attempt, and the installed LifeOS Safety hook returned external-content and injection-shape warnings. See the [browser safety record](../notes/2026-09-28-browser-content-safety.md).

## Outbound firewall and Discord scope

The account's persistent egress rule in `/etc/lifeos-hermes-test-egress.nft` allows UID 1004 to send outbound TCP traffic on port 443 to any destination before its LAN-only reject rules. The service `lifeos-hermes-test-egress.service` is enabled and active. The prior ruleset is backed up at `/etc/lifeos-hermes-test-egress.nft.before-discord-20260928-082859`. This exception enabled Discord package installation and the bot connection. It is broader than a Discord-only allowlist. Other outbound Internet ports remain blocked by the rules shown in that file. The plugin does not install or manage this firewall rule.

## Private development logging

The account has an external recorder at `~/workspace/development-hook-capture/development`. A startup file in the managed base Python interpreter loads source-pinned observers in gateway, dashboard, and detached hook processes. Hermes, LifeOS, and public plugin runtime files remain unchanged by this logging installation.

The private configuration is `~/.config/lifeos-development-capture/config.json`. Raw event files and compressed artifacts are under `~/.local/state/lifeos-development-capture`, with directory mode 0700 and file mode 0600. The run ID is `development-20260930T140347Z`. Logs retain ordinary conversation content and filter recognized credentials. They are not copied into the installed public plugin or committed to Git.

The [development capture record](../notes/2026-09-30-development-capture-212.md) gives the tests, coverage snapshot, review procedure, and removal steps. This recorder is active for development use. No recurring analysis job or automatic retention policy is configured.

LifeOS Doctor now reports that every registered hook interpreter resolves. The bridge executes mapped events through the Hermes plugin API and generic core extensions in the test fork. The [hook parity record](hook-parity.md) identifies unverified effects and missing events. Full hook parity has not been verified. Pulse reports a missing Bunker module from the public LifeOS fixture, but its hook routes remain active. Optional external services such as voice, Cloudflare, and a GitHub login are not configured in the fixture.

A second account, `lifeos-install-probe`, verifies a clean layout with distinct `~/.claude` and `~/.hermes` roots. It mounted LifeOS, installed the public plugin at a pinned commit, and ran native prompt hooks from an accessible working directory. It has no model credentials. See [the clean install probe](../notes/2026-09-28-clean-install-probe.md).
