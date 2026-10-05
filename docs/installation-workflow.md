# Plugin-managed LifeOS installation

The intended order is Hermes, LifeOS Bridge plugin, then LifeOS. [Fresh installation path checks](verification/2026-10-05-fresh-store-paths/README.md) bind the native program and data selectors to the selected home. They preserve an unrelated retained store. The plugin must load before LifeOS exists so its settings page can guide installation. An absent `~/.claude/settings.json` now leaves its hooks inactive without making the plugin fail to load.

## Requested page flow

The [overall memory plan](memory-implementation-plan.md#installation-trial-and-removal-requirements) adds three planned evaluation choices: a separate trial profile, current-profile activation with reviewed memory import, and current-profile activation without import. Installing the plugin or LifeOS must not select memory ownership automatically. Profile isolation and shared Hermes code changes require separate acceptance evidence.

The page must also offer a verified return to Hermes before removing the integration. It must distinguish restoring preserved Hermes memory from exporting selected current LifeOS facts. Data deletion is a separate owner action. The candidate now has [private import review and recoverable item publication](verification/2026-10-05-memory-import/README.md). Complete established-installation and removal workflows remain open. The fresh-install controls below do not verify them.

The candidate's [named-store preparation](verification/2026-10-05-named-fresh-store/README.md) initializes Adrian and Cerebo in a separate private native store. It retains existing facts and Hermes files outside that store. All six native tools complete with Bun 1.3.14 and verified locks for 12 package trees. The installer seeds locks only in an empty target and cancels each native process group after timeout or interruption. The two native tests and 20 installer tests pass. This primitive still requires authenticated page controls, selection, recovery, activation, and return acceptance.

The [authenticated preparation endpoint](verification/2026-10-05-fresh-store-http/README.md) now accepts the two display names under the current owner binding. The server selects the source and destination. Native HTTP acceptance and four neighboring route tests pass. Page controls, restart-safe preparation, status, selection, recovery, activation, and return remain required.


1. The page checks whether LifeOS is missing, partial, or installed.
2. **Prepare latest LifeOS** reads the current commit of [Daniel Miessler's public repository](https://github.com/danielmiessler/LifeOS), clones that exact revision, applies the bundled LifeOS patches, and publishes a private candidate. It changes no running files.
3. **Install prepared LifeOS** shows the exact commit and patch count before use. It validates the candidate again, creates a new private `~/.claude` directory, runs six LifeOS installation tools, and checks the version and hook settings. It refuses any existing `~/.claude` directory. If a tool fails, it moves the partial directory to a private `failed-install-*` directory for inspection. A separate `.212` account completed this path for LifeOS 7.40.4, with 11 hook event groups and 27 hook entries. The isolated acceptance installation also verifies this button through an authenticated browser. See [the browser acceptance record](verification/2026-10-02-mount-acceptance/README.md).
4. **Finish LifeOS setup** runs the installed `Mount.ts`, checks its rendered Hermes files, runs `hermes config check`, and creates a VersionDrift baseline from the prepared source and installed system files. It requires an existing Hermes configuration and command. Before mounting, it saves `config.yaml`, `SOUL.md`, `.env`, and the `lifeos` guard plugin in a private snapshot. A failed mount, check, or baseline creation restores those Hermes files. The page then asks for a gateway restart. It does not select a Hermes model or restart the gateway itself.
5. The page explains the stock Hermes limits. Leaving Hermes stock selects reduced mode. **Prepare tested Hermes extension** builds a private candidate from a clean source checkout at the one tested base commit and all nine bundled Hermes patch groups. **Apply tested Hermes extension** stages only the changed Hermes files and config, then starts a detached user systemd worker. The worker stops the gateway, installs the files, restarts the service, and checks the new process and Hermes config. If a check fails, it restores the stock files and restarts the gateway. The page polls the snapshot state and offers **Restore previous Hermes** after a successful apply. The [separate service probe](../notes/2026-09-29-hermes-only-patch.md) exercised the installed API apply and restore routes and a private model call through patched Hermes. An authenticated HTTP request, browser click, and complete paired evidence remain open.
6. Updates must repeat the revision, patch, test, and rollback checks. The LifeOS update worker stages system files, dependencies, and exact owned hook registrations. The separate operator release transaction covers Hermes and plugin code.

The latest upstream LifeOS commit was `5e2f2e8c0abde612da0e99c16c0d07d4ec21b88c` when checked on 2026-09-29. That is the current tested base. If upstream moves, preparation refuses the new commit until its patch set and behavior tests are ported. A clean patch application alone is not a parity result. The page must not label an untested future commit as compatible.

The separate `.212` installation account completed the mount, a real Hermes config check, and a baseline of 1,796 installed system files with zero changes immediately afterward. It then used the private LAN model for stock and patched Hermes requests. The installed plugin API started a gateway patch and restore, with a running service and clean stock checkout afterward. The fresh LifeOS installation and finalization buttons also pass authenticated browser acceptance. Hermes extension browser acceptance remains separate. The current fresh install is limited to an account with no `.claude` directory. Existing Claude Code users need an update or migration path that preserves their files.

The Hermes preparation and apply paths require an editable, clean source checkout at `758ad514eb0e800547e015edf05aa18f78b78d82` and a running `hermes-gateway.service` user service whose launcher points into that checkout. A packaged Hermes install or a later source revision will be refused. The host-only worker does not update plugin dependencies or LifeOS files. It keeps a private snapshot for recovery and rejects a source or config change between staging and apply.

## Managed memory authorization

Finalization, LifeOS update, and update recovery require an authenticated Hermes dashboard session. If the profile has managed memory configuration or a native connector, the account must also have a current installation owner binding. Missing or revoked bindings refuse managed mounting. Conversation metadata and fabricated owner headers cannot supply this authority.

The plugin issues a short-lived grant for the fixed installation and profile. The grant permits native prompt operations only. Update grants also bind the queued request and action. The worker checks authority before systemd operations. Recovery requires a fresh authenticated grant. A failed recovery launch restores the prior request and status so the owner can retry.

Recovery authority is separate from mount authority. It permits snapshot recovery without exposing memory or prompt operations. A missing installed directory does not prevent owner-authorized recovery after an interrupted directory swap. The worker still checks the exact job, action, and current profile configuration.

The [administration evidence](verification/2026-10-02-memory-administration/README.md) covers actual native mounting and authenticated finalization. Update launch and recovery tests use component fixtures for systemd operations. The isolated acceptance record adds real browser and gateway checks. Complete memory ownership acceptance remains required. These controls do not select lasting-memory ownership, approve source contents, or import existing Hermes memory.

## Reduced mode with stock Hermes

The runtime registers only hooks present in the pinned stock Hermes source. Its manifest validated without findings against that source on `.212`. The reduced path is an experimental integration and does not provide the LifeOS safety contract:

| LifeOS behavior | Stock Hermes path | Limit |
| --- | --- | --- |
| PreToolUse | `pre_tool_call` | The callback can inspect tool calls. This mode still needs a live paired tool run. |
| PostToolUse and PostToolUseFailure | `post_tool_call` observer | Native handlers can run and record side effects. Their returned advice is not reliably appended after another result transformer. |
| SessionStart and UserPromptSubmit | `pre_llm_call` | Context can be added. A LifeOS prompt block is not enforced by the stock host. |
| SessionEnd and API request errors | Stock lifecycle events | Handlers can run when the host emits those events. Exact reason and restart coverage remains open. |
| Bash PermissionRequest | No equivalent command approval callback | LifeOS Bash permission allow, ask, deny, and replacement decisions are not enforced. Hermes keeps its own approval rules. |
| Command policy on every Bash call | No extended command-policy callback | LifeOS cannot check a command that stock Hermes would run without an approval warning. Manual allowlists, prepared desktop approvals, and bypass modes do not receive the tested LifeOS denial precedence. |
| PermissionRequest replacement | No tested command replacement and recheck path | A native hook cannot safely substitute a Bash command and have the replacement checked again before execution. File and Model Context Protocol replacement still need separate stock-host validation. |
| Stop answer gates | No pre-delivery continuation or failure callback | LifeOS cannot withhold a rejected answer before delivery and history persistence. |
| Child model route | No tested per-child provider and effort contract | The plugin cannot promise Hermes provider selection for each LifeOS tier. |
| Remote file guard | No tested stale-write patch | SSH and Docker whole-file writes lack the tested guard supplied by our Hermes patch. |
| Nested tool identity | No tested `execute_code` session propagation | Inner tool calls can lose the parent LifeOS session and transcript identity. |
| Session reasons | Basic finalization event only | Empty-session clear and resume, prompt exit, and gateway resume lack the tested reason paths supplied by the patch set. |
| Turn completion and watchdog activity | No `on_turn_result` callback | The bridge cannot observe the tested final-turn activity signal used by its watchdog and transcript cleanup. |
| Scheduled worker runtime | No tested cron worker bootstrap patch | A source installation can start a worker outside the managed dependency environment needed by this plugin. |

The patched source exposes the missing hooks and fixes additional command, model, session, and worker paths. It is still an experimental compatibility set. Full parity requires the paired registration matrix and live release checks in the [resolution plan](parity-resolution-plan.md).
