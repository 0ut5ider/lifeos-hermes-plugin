# LifeOS plugin for Hermes

This project connects an installed LifeOS hook set to Hermes through a separate plugin. The goal is to preserve LifeOS's hook behavior while keeping the integration outside the LifeOS repository.

**Status:** Experimental test fixture. The bridge runs native LifeOS hooks at matching Hermes events. Full hook parity is not yet achieved. Do not use this repository as a replacement for a working LifeOS installation.

## Compatibility target

- Load LifeOS context and skills from a configurable installation path.
- Map each LifeOS hook behavior to a Hermes lifecycle point and verify its effect, including blocks, approvals, context injection, and stop gates.
- Keep the LifeOS installation unchanged where possible. Record any Hermes core extension needed for behavior the plugin API cannot express.
- Test locally on one host first. A remote LifeOS installation is a separate deployment mode.

See the [LifeOS installation guide](https://github.com/danielmiessler/LifeOS/blob/main/LifeOS/INSTALL.md) and the [Hermes event hook reference](https://hermes-agent.nousresearch.com/docs/user-guide/features/hooks) for the current upstream contracts.

The plugin can load before LifeOS is installed. Its dashboard prepares the latest tested LifeOS source, installs it into an empty `~/.claude` directory, mounts it into an existing Hermes installation, and records a VersionDrift baseline. A fresh `.212` account completed these file and config steps. On stock Hermes, the plugin registers a reduced set of callbacks; [the installation workflow](docs/installation-workflow.md) lists the missing safety and model-routing behavior. The page can prepare and apply a tested Hermes extension from an exact, clean source checkout, then restore the prior code if needed. A separate `.212` service account exercised the installed API routes, gateway restart, and a private model call through patched Hermes. The LifeOS update worker stages system files, dependencies, and hook registrations, then restarts and verifies the gateway with a recoverable snapshot. The [transaction rehearsal](notes/2026-09-29-lifeos-update-transaction.md) passed apply, restore, and forced rollback at the current pinned revision. GitHub's `main` still pointed at that revision on 2026-09-29, so a newer upstream revision was unavailable to test. An authenticated browser click and full hook parity remain open.

The [hook parity record](docs/hook-parity.md) lists mapped events, tested effects, and missing behavior. The [parity resolution plan](docs/parity-resolution-plan.md) sets the comparison and completion gates. The [live paired ledger](docs/parity/paired-live-coverage.json) records dispatch, exit code, and output presence for 63 of 74 registrations from native Claude Code and Hermes sessions. It does not establish side-effect parity. The [trace note](notes/2026-09-29-paired-hook-trace.md) records the fixture, limits, and a 19-test SSH and Docker gate that passed without skips. Three [paired permission outcomes](docs/parity/paired-permission-rewrites.json) have a separate machine-checked comparison. The isolated Hermes installation and its current limits are recorded in [docs/test-environment.md](docs/test-environment.md). The [clean install guide](docs/clean-install.md) uses separate LifeOS and Hermes roots. Follow the [Discord setup guide](docs/discord-setup.md) for a new messaging gateway. A separate [Claude Code reference installation](docs/claude-reference.md) uses synthetic LifeOS data and the same local model to measure native hook behavior.

Read the [update policy](docs/update-policy.md) before updating Hermes, LifeOS, or this plugin. The LifeOS update control accepts only a prepared, tested compatibility set. Hermes source and bridge plugin updates still require a separate release transaction.

The [upstream Hermes proposal](docs/upstream-hermes-proposals.md) separates generic host fixes and plugin APIs from the LifeOS-specific bridge. It records existing upstream issues and the verification required before removing a local patch.

The [VersionDrift baseline guide](docs/version-drift-baseline.md) explains the plugin-owned baseline, dashboard review action, update procedure, and native hook timing. It keeps Git metadata out of the shared Hermes home.

## Lasting memory, experimental

The [resolved memory experience](notes/2026-09-30-memory-design.md) gives LifeOS ownership of lasting facts and preferences. Hermes keeps conversation history, compression, and skills. Other agents can optionally share the same native records through an authenticated Model Context Protocol (MCP) connection. The policy applies across messaging apps. The [design review](docs/agents/2026-09-30-memory-design-review/memory-design-review.md) and [implementation plan](docs/memory-implementation-plan.md) describe the required boundaries and acceptance evidence.

The implementation includes governed native fact and proposal operations, a Hermes provider, required model-request checks, optional SSH enrollment, and development preferences. The page exposes manual proposal decisions and source adoption. Adoption preserves native files and keeps unclassified notes private. [Real-agent ownership checks](notes/2026-09-30-memory-host-ownership.md) establish the two Hermes store flags that setup must disable. A [complete remember turn](notes/2026-09-30-memory-agent-turn.md) verifies actual native persistence and receipt propagation. [Conversation repair](notes/2026-09-30-memory-history-repair.md) handles corrections and forgetting inside an admitted owner turn, including native recall. Its independent closure passes 71 tests. [Background skill review](notes/2026-09-30-memory-background-review.md) now creates or stages native Hermes skills while both lasting stores stay disabled. The expanded independent closure passes 81 tests, including the next foreground turn.

**Memory ownership remains disabled on running installations.** Complete source coverage, restricted prompts and delivery, resume repair, changed installed prompts, full compression rotation, and recoverable ownership setup remain open. The implementation does not connect to the existing `.211` or `.213` stores. The current evidence does not establish complete memory activation.

The [2026-09-29 test-server release](notes/2026-09-29-release-212.md) records the deployment of the reviewed patch reduction to the active `.212` account. This account keeps its original shared LifeOS and Hermes root. A new server must use the separate roots in the clean install guide. The shared-root account cannot use the separate-root LifeOS update worker.

The plugin declares pinned Python dependencies for `tree-sitter`, `tree-sitter-bash`, `pathspec`, and `mcp` (2.0.0) for Bash parsing, file-rule matching, and the optional memory protocol service. Hermes asks for dependency consent when installing or enabling the plugin and retains those packages through managed updates. Run `hermes plugins validate PATH --install-deps` against the downloaded plugin before enabling it. A missing parser prevents the bridge from loading rather than silently dropping deny rules. See [the compound Bash probe](notes/2026-09-28-compound-bash-permissions.md).

The tested extension contains nine Hermes patch groups and ten LifeOS patches. Use source preparation or the plugin's installation controls to apply the complete bundle in its declared order. The [patch footprint guide](docs/patch-footprint.md) explains each group, the plugin-owned commands, and the verified native capability record. Hermes's required prompt, command, and final-answer gates remain active. The [hook parity record](docs/hook-parity.md) describes the supported base revisions and remaining limits.

Local project hook registrations run only when the project root appears in Hermes's `skills.trusted_project_dirs`. SSH project hooks require a separate trust file that binds the project root to the SSH host, user, and port. A project settings file can contain shell commands, so the bridge does not execute it from an untrusted checkout.

For an SSH workspace, create `~/.config/lifeos-hook-bridge/remote-projects.json` as the Hermes account with mode `0600`. Add only project roots whose hook commands you trust:

```json
{"projects":[{"type":"ssh","host":"example.internal","user":"agent","port":22,"root":"/home/agent/workspace"}]}
```

The `host`, `user`, `port`, and `root` must match the active Hermes SSH backend. For a Docker backend, use `{"type":"docker","image_id":"sha256:<64 hex digits>","root":"/workspace"}` instead. Get the immutable image ID with `docker image inspect --format '{{.Id}}' <image>`. The bridge checks the backend's physical path before loading `.claude/settings.json` and `.claude/settings.local.json`. It runs their command hooks inside that backend and sends HTTP hooks only to that backend's loopback address. Remote command transport requires Bash and `base64`; HTTP hooks also require `curl`. Set `LIFEOS_REMOTE_PROJECT_TRUST` in the Hermes process environment to use another trust-file path. Other remote backend types are not yet supported.

## Install the plugin

Install Hermes and configure a model first. Then install this plugin into Hermes. In its settings page, prepare and install the tested LifeOS source, then select **Finish LifeOS setup**. That action mounts LifeOS into Hermes and records a baseline. Restart the gateway after it succeeds. Stock Hermes provides the reduced behavior listed in [the installation workflow](docs/installation-workflow.md). On the pinned clean source checkout, the page can prepare and apply the tested Hermes extension through a detached gateway restart worker. Its **Restore previous Hermes** control reverses the code patch. The [test environment record](docs/test-environment.md) gives the revisions used for verification.

The [source preparation command](docs/clean-install.md) applies this exact patch order from pinned public base revisions into two new trees. It checks every patch and writes `source-manifest.json` before publishing the output directory. The separate [system overlay snapshot tool](scripts/system_overlay_snapshot.py) saves changed LifeOS system files for a verified rollback. Run the rest of the clean install from those prepared trees.

Clone this repository and get the full commit ID for the tested branch:

```sh
git rev-parse origin/feature/initial-scaffold
```

Use that 40-character ID in Hermes's Git installer:

```sh
hermes plugins install 0ut5ider/lifeos-hermes-plugin/lifeos_hook_bridge --ref <full-commit-id> --no-deps --no-enable
hermes plugins enable lifeos-hook-bridge
```

The install source is the `lifeos_hook_bridge/` directory, which contains only runtime files. The full repository includes tests and notes that cause Hermes's installer to report a caution scan verdict. The runtime directory passed the Hermes scan in the isolated test profile without `--force`. The plugin reads native hook registrations from `~/.claude/settings.json`; set `LIFEOS_HOOK_SETTINGS` in the Hermes process environment if the file is elsewhere. Restart the Hermes gateway after enabling the plugin. Restart the Hermes dashboard after installing the plugin so it can mount the LifeOS settings API.

The Git installer was verified against pinned public commits in the separate clean-install account on `.212`. The plugin enabled, a native LifeOS prompt hook returned context, and the clean account completed a private LAN model call. The [release gate record](notes/2026-09-29-release-gate.md) gives the current installation, update, rollback, Hermes test, and SSH and Docker results. The gate remains blocked by eleven unobserved native hook registrations and other behavior cases in the [parity plan](docs/parity-resolution-plan.md). No test result here establishes full Claude Code hook parity.

Open **LifeOS Bridge** in the Hermes dashboard sidebar, or visit `/lifeos-bridge`. Each Haiku, Sonnet, Opus, and Fable row has a picker populated from Hermes's configured model catalog and an independent effort selector. An empty, unconfigured tier uses Hermes's current provider and model automatically. The page shows that pair in each empty row and offers to save it. Saving makes the choice stay fixed if the Hermes main model changes later. Add or authenticate models on Hermes's Models page first. Save changed LifeOS settings and restart the Hermes gateway. The effort defaults are Haiku at low, Sonnet at medium, and Opus and Fable at xhigh. The advanced Pinned LifeOS tier defaults to Fable when LifeOS `settings.json` names a local model; a Claude tier pin in that file takes priority.

The Stop hook limit selector defaults to **Claude Code behavior**: after the configured continuation limit, Hermes allows the last answer. Select **Fail the turn** to withhold that answer and return an incomplete result instead. Either setting withholds earlier rejected drafts from user delivery and Hermes session history. Iteration-budget exhaustion always fails the turn.

Required prompt, command, and final-answer callbacks stop the operation if they raise an exception or exceed the callback deadline. The extended host uses `pre_prompt_admission` for LifeOS prompt checks. Stock Hermes uses its optional `pre_llm_call` callback and cannot guarantee this failure behavior. The dashboard reports older extended hosts without the admission event as partial. Install the complete tested host patch bundle before selecting full functionality. See [the review corrections](notes/2026-09-29-review-correctness-fixes.md).

A session review grant covers the reviewed command, target backend, and working directory. The plugin asks again for another workspace or target. Hermes still enforces a later denial. A failed required final check fails the turn immediately; it does not consume the configured continuation limit. When several valid final checks reject an answer, any check that requires failure at the limit retains that requirement.

When a tier uses a Hermes provider and model, the LifeOS child launcher uses Hermes's installed runtime and that provider's credentials automatically. It does not need a separate gateway token in `model.env`. The direct provider route does not fall back to another provider when the selected provider fails. **Keep existing child routing (advanced)** is an explicit per-tier choice. Delegated Agent children then inherit the parent Hermes model, while direct inference uses `ANTHROPIC_MODEL` and the Anthropic Messages compatible gateway from `model.env` when direct mode is enabled. For that separate gateway route, set `LIFEOS_CHILD_INFERENCE_DIRECT=1` and keep `ANTHROPIC_BASE_URL`, `ANTHROPIC_AUTH_TOKEN`, and `ANTHROPIC_MODEL` in `model.env` with mode `0600`. Without direct mode, the child launcher passes the selected model and effort to the installed Claude CLI. A launcher started outside Hermes needs `LIFEOS_MODEL_TIER_MAP` in its environment to use plugin settings. The direct path accepts LifeOS text requests and image file references. For the Hermes integrity gate, run `hermes lifeos-probe --run` once and repeat it after changing the Fable route. The probe evidence expires after 30 days. `CarrierProbe.ts` remains the Claude Code specific test. See [the direct inference probe](notes/2026-09-28-direct-child-inference.md).

## Development evidence

Development evidence is collected with an [external recorder](development/README.md). It is excluded from the installed plugin. Captured prompts, tool data, and hook streams stay in a private directory outside this repository.

The recorder is active on `.212`. Its [deployment record](notes/2026-09-30-development-capture-212.md) gives verified boundaries, coverage limits, private paths, and removal steps. The `.212` bot accepts ordinary messages in its dedicated `#hermes-212` channel. The [completed logging review](notes/2026-09-30-logging-review-fixes.md) records verified corrections and the updated deployment. No scheduled analysis or automatic log deletion is configured.

## Reminder routing and privacy

LifeOS's `ReminderRouter` hook creates a GitHub issue containing the original prompt when `WORK.REPO` is configured and the prompt matches an explicit reminder, research, or queue phrase. The isolated test account has no `WORK.REPO`, so this route is inactive there. Decide where reminder text may be stored before enabling that configuration in a private deployment. See [the egress record](notes/2026-09-28-reminder-router-egress.md).

## License

MIT. See [LICENSE](LICENSE).
