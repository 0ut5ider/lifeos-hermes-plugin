# LifeOS plugin for Hermes

This project connects an installed LifeOS hook set to Hermes through a separate plugin. The goal is to preserve LifeOS's hook behavior while keeping the integration outside the LifeOS repository.

**Status:** Experimental test fixture. The bridge runs native LifeOS hooks at matching Hermes events. Full hook parity is not yet achieved. Do not use this repository as a replacement for a working LifeOS installation.

## Compatibility target

- Load LifeOS context and skills from a configurable installation path.
- Map each LifeOS hook behavior to a Hermes lifecycle point and verify its effect, including blocks, approvals, context injection, and stop gates.
- Keep the LifeOS installation unchanged where possible. Record any Hermes core extension needed for behavior the plugin API cannot express.
- Test locally on one host first. A remote LifeOS installation is a separate deployment mode.

See the [LifeOS installation guide](https://github.com/danielmiessler/LifeOS/blob/main/LifeOS/INSTALL.md) and the [Hermes event hook reference](https://hermes-agent.nousresearch.com/docs/user-guide/features/hooks) for the current upstream contracts.

The [hook parity record](docs/hook-parity.md) lists mapped events, tested effects, and missing behavior. The isolated Hermes installation and its current limits are recorded in [docs/test-environment.md](docs/test-environment.md). A separate [Claude Code reference installation](docs/claude-reference.md) uses synthetic LifeOS data and the same local model to measure native hook behavior.

The bridge needs the [Hermes core extension](patches/hermes-hook-controls.patch) for Stop, approval, and prompt-block behavior. Apply the [Hermes remote file guard patch](patches/hermes-remote-file-staleness.patch) after that extension to prevent stale whole-file writes through SSH and other non-host backends. The [LifeOS task patch](patches/lifeos-task-governance.patch) lets the native TaskCreated hook use a Hermes session count. Apply the [LifeOS watchdog patch](patches/lifeos-agent-watchdog.patch) after the task patch to route background agent silence alerts through Hermes. The [LifeOS terminal audit patch](patches/lifeos-terminal-audit.patch) records Hermes's combined terminal output under an accurate audit field. The [LifeOS checkpoint patch](patches/lifeos-checkpoint-verification.patch) runs repository verification hooks and keeps failed checkpoints pending. The [LifeOS failure capture patch](patches/lifeos-failure-capture.patch) pairs transcript tool results with their calls. The [LifeOS remote desktop gate patch](patches/lifeos-remote-desktop-gate.patch) keeps remote turns from changing local terminal state. The [LifeOS remote ISA view patch](patches/lifeos-remote-isa-view.patch) lets its native stale-write hook use a digest from the active Hermes backend. These patches are tested on the isolated `.212` checkout. The hook parity record describes their exact base revisions and remaining limits.

Local project hook registrations run only when the project root appears in Hermes's `skills.trusted_project_dirs`. SSH project hooks require a separate trust file that binds the project root to the SSH host, user, and port. A project settings file can contain shell commands, so the bridge does not execute it from an untrusted checkout.

For an SSH workspace, create `~/.config/lifeos-hook-bridge/remote-projects.json` as the Hermes account with mode `0600`. Add only project roots whose hook commands you trust:

```json
{"projects":[{"type":"ssh","host":"example.internal","user":"agent","port":22,"root":"/home/agent/workspace"}]}
```

The `host`, `user`, `port`, and `root` must match the active Hermes SSH backend. For a Docker backend, use `{"type":"docker","image_id":"sha256:<64 hex digits>","root":"/workspace"}` instead. Get the immutable image ID with `docker image inspect --format '{{.Id}}' <image>`. The bridge checks the backend's physical path before loading `.claude/settings.json` and `.claude/settings.local.json`. It runs their command hooks inside that backend and sends HTTP hooks only to that backend's loopback address. Remote command transport requires Bash and `base64`; HTTP hooks also require `curl`. Set `LIFEOS_REMOTE_PROJECT_TRUST` in the Hermes process environment to use another trust-file path. Other remote backend types are not yet supported.

## Install the plugin

Install Hermes with the [core hook extension](patches/hermes-hook-controls.patch), then apply the [remote file guard patch](patches/hermes-remote-file-staleness.patch). Install LifeOS with its native Claude Code hooks. Apply the [task patch](patches/lifeos-task-governance.patch) to the compatible LifeOS checkout, then apply the [watchdog patch](patches/lifeos-agent-watchdog.patch), [terminal audit patch](patches/lifeos-terminal-audit.patch), [checkpoint patch](patches/lifeos-checkpoint-verification.patch), [failure capture patch](patches/lifeos-failure-capture.patch), [remote desktop gate patch](patches/lifeos-remote-desktop-gate.patch), and [remote ISA view patch](patches/lifeos-remote-isa-view.patch). The [test environment record](docs/test-environment.md) gives the revisions used for verification. Check each patch with `git apply --check` before applying it to a different revision.

Clone this repository and get the full commit ID for the tested branch:

```sh
git rev-parse origin/feature/initial-scaffold
```

Use that 40-character ID in Hermes's Git installer:

```sh
hermes plugins install 0ut5ider/lifeos-hermes-plugin/lifeos_hook_bridge --ref <full-commit-id> --no-enable
hermes plugins enable lifeos-hook-bridge
```

The install source is the `lifeos_hook_bridge/` directory, which contains only runtime files. The full repository includes tests and notes that cause Hermes's installer to report a caution scan verdict. The runtime directory passed the Hermes scan in the isolated test profile without `--force`. The plugin reads native hook registrations from `~/.claude/settings.json`; set `LIFEOS_HOOK_SETTINGS` in the Hermes process environment if the file is elsewhere. Restart the Hermes gateway after enabling the plugin.

The Git installer was verified on the isolated `.212` account with a temporary local Git source and a disabled probe name. The probe plugin was removed afterward. The account blocks outbound downloads, so a direct GitHub install was not tested there. The core extension applied to public Hermes commit `bac0c45d` on 2026-09-28, and the remote file guard patch passed `git apply --check` on that patched source. A live SSH regression on `.212` refused an external edit that Hermes previously overwrote. All seven LifeOS patches applied to public LifeOS HEAD `5e2f2e8`. The current plugin suite passed 153 tests on `.212` with Bun on `PATH`; 40 optional fixture tests skipped. Five live SSH tests and two live Docker tests passed separately with disposable projects. Discord delivery remains unverified in the test account.

The optional child launcher can run ordinary LifeOS inference directly through an Anthropic Messages compatible local gateway. Put `ANTHROPIC_BASE_URL`, `ANTHROPIC_AUTH_TOKEN`, `ANTHROPIC_MODEL`, and `LIFEOS_CHILD_INFERENCE_DIRECT=1` in the private `~/.config/lifeos-hook-bridge/model.env` file. Keep it readable only by the account. The direct path accepts LifeOS text requests and image file references. It does not emulate Claude Code tool dispatch; `CarrierProbe.ts` still requires Claude Code to test that Claude-specific behavior. See [the direct inference probe](notes/2026-09-28-direct-child-inference.md).

## Reminder routing and privacy

LifeOS's `ReminderRouter` hook creates a GitHub issue containing the original prompt when `WORK.REPO` is configured and the prompt matches an explicit reminder, research, or queue phrase. The isolated test account has no `WORK.REPO`, so this route is inactive there. Decide where reminder text may be stored before enabling that configuration in a private deployment. See [the egress record](notes/2026-09-28-reminder-router-egress.md).

## License

MIT. See [LICENSE](LICENSE).
