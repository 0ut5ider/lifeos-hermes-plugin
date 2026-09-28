# Isolated LifeOS test environment

As of 2026-09-28, the development fixture is an unprivileged Linux account with a fresh Hermes installation and a fresh clone of the public LifeOS repository. No LifeOS data was copied from an existing installation. The principal is the fictional `Test Operator`.

## Installed baseline

- Hermes v0.21.5 with the generic hook-control test branch at `1c9dbc73f`, a local model, a LAN dashboard, and a separate Discord test bot. The branch also has the remote whole-file write guard, Stop effort forwarding, and per-child delegation model and effort routing. The hook, delegation, and cron worker changes are published as five patches in this repository.
- LifeOS at base commit `5e2f2e8`, deployed into `~/.hermes` with `DeployCore.ts --config-root ~/.hermes --apply`. The isolated checkout has a local `feature/hermes-task-hook` branch at `af60000` with TaskGovernance, AgentWatchdog, EventLogger, CheckpointPerISC, FailureCapture, KittyEnvPersist, tab-setter, ISAStaleWriteGuard, and ModelRungGuard changes installed in the test account. All eight compatibility patches are shipped in this plugin repository.
- A fresh personal tree from `ScaffoldUser.ts --config-root ~/.hermes --apply`, linked by `LinkUser.ts --config-root ~/.hermes --apply`.
- LifeOS's shipped Hermes sidecar mount, including its identity renderer and guard plugin.
- LifeOS's 74 native Claude Code hook registrations installed in the test account, plus the separate `lifeos-hook-bridge` Hermes plugin.
- Bun 1.4.2 and ripgrep 15.2.0.
- The private child-model configuration enables the plugin's direct Anthropic Messages adapter. Native LifeOS inference no longer starts Claude Code for ordinary text or image requests. Claude Code remains installed for reference tests.
- The Discord extra is installed through `hermes pm install --extra discord`. The `hermes-gateway.service` user service is enabled, and systemd linger keeps it running after logout.
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

## Outbound firewall and Discord scope

The account's persistent egress rule in `/etc/lifeos-hermes-test-egress.nft` allows UID 1004 to send outbound TCP traffic on port 443 to any destination before its LAN-only reject rules. The service `lifeos-hermes-test-egress.service` is enabled and active. The prior ruleset is backed up at `/etc/lifeos-hermes-test-egress.nft.before-discord-20260928-082859`. This exception enabled Discord package installation and the bot connection. It is broader than a Discord-only allowlist. Other outbound Internet ports remain blocked by the rules shown in that file. The plugin does not install or manage this firewall rule.

LifeOS Doctor now reports that every registered hook interpreter resolves. The bridge executes mapped events through the Hermes plugin API and generic core extensions in the test fork. The [hook parity record](hook-parity.md) identifies unverified effects and missing events. Full hook parity has not been verified. Pulse reports a missing Bunker module from the public LifeOS fixture, but its hook routes remain active. Optional external services such as voice, Cloudflare, browser verification, and a GitHub login are not configured in the fixture.
