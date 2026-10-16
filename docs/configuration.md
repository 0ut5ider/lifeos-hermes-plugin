# Configure LifeOS in Hermes

Use **LifeOS Bridge** at `/lifeos-bridge` for runtime settings. Use **LifeOS releases** at `/lifeos-releases` for complete-package installation and updates. Owner authorization for lasting memory remains a separate review.

## Models and effort

The Haiku, Sonnet, Opus, and Fable rows are LifeOS tiers. Each row selects a provider/model pair from the Hermes catalog and an independent effort. An empty, unconfigured row uses Hermes's current provider and model. Saving that pair fixes the selection even if the main Hermes model changes later.

Add or authenticate a model through Hermes's Models page before selecting it here. The default efforts are:

| Tier | Effort |
| --- | --- |
| Haiku | `low` |
| Sonnet | `medium` |
| Opus | `xhigh` |
| Fable | `xhigh` |

Several tiers can use the same model with different efforts. The advanced **Pinned LifeOS tier** defaults to Fable when native `settings.json` names a local model. A native Claude tier pin takes priority. Keep the configured mapping unless the owner requests a model change.

Save the settings and restart the gateway after active work finishes. A changed model route can require a new lasting-memory owner review. Run `hermes lifeos-probe --run` after configuring the Fable route and after changing it. The probe makes an actual delegated model request. Its evidence expires after 30 days. Native `CarrierProbe.ts` remains specific to Claude Code.

## Advanced child routing

The normal Hermes route uses its installed runtime and selected provider credentials. It does not require a separate child gateway token. A selected provider failure does not cause fallback to a different provider.

**Keep existing child routing (advanced)** is a per-tier choice. Delegated children then inherit the parent Hermes model. Direct inference can use the separately configured Anthropic-compatible route when direct mode is enabled. Otherwise the native child launcher uses the installed Claude CLI. These are separate routes with separate prerequisites; selecting the option does not configure that service or authenticate it.

For implementation details, read [`model_tiers.py`](../lifeos_hook_bridge/model_tiers.py), [`bin/claude`](../lifeos_hook_bridge/bin/claude), and [`claude_direct.py`](../lifeos_hook_bridge/bin/claude_direct.py). The [direct-inference investigation](../notes/2026-09-28-direct-child-inference.md) retains the earlier probe and environment contract. Keep credential values private.

## Stop hook policy

**Claude Code behavior** allows the last answer after the configured continuation limit. **Fail the turn** withholds that answer and returns an incomplete result instead. Earlier rejected drafts remain withheld under either setting. Iteration-budget exhaustion always fails the turn.

Required prompt, command, and final-answer checks stop the operation when they fail or exceed their deadline. Stock Hermes callbacks do not supply every required admission behavior. Use the complete qualified package for the full contract. See [hook parity](hook-parity.md).

## Native home and hook settings

The selected LifeOS home determines the installed root and user data. A store-selection transaction updates those bindings and services together. Do not swap `~/.claude` links or edit an operation journal to change stores. [Selection design and recovery](fresh-store-selection.md) retains the implementation details.

The bridge normally reads native hook registrations from the selected home's `.claude/settings.json`. `LIFEOS_HOOK_SETTINGS` can select a different settings file in the Hermes process environment. That override does not change memory authority or qualify another native source tree.

VersionDrift baselines bind reviewed source and installed system files. Review the file list and changed source before renewing a baseline. A clean baseline is not proof that a new upstream combination passes behavior checks.

## Trusted remote project hooks

Remote project hooks require an explicit trust file for the Hermes account, normally `~/.config/lifeos-hook-bridge/remote-projects.json`, with mode `0600`. Use only project roots whose commands you trust. Example SSH entry:

```json
{"projects":[{"type":"ssh","host":"example.internal","user":"agent","port":22,"root":"/home/agent/workspace"}]}
```

The host, user, port, and root must match the active Hermes SSH backend. For Docker, bind the immutable image ID and project root:

```json
{"projects":[{"type":"docker","image_id":"sha256:<64 hex digits>","root":"/workspace"}]}
```

Get the actual immutable image ID with `docker image inspect --format '{{.Id}}' IMAGE`. The bridge verifies the backend's physical path before loading project settings. Commands execute inside that backend. HTTP hooks may target only its loopback address. The transport requires Bash and `base64`, plus `curl` for HTTP hooks.

`LIFEOS_REMOTE_PROJECT_TRUST` can select another trust-file path in the Hermes process environment. Other remote backend types are not supported by this runner. Remote project execution is separate from external agents connecting to memory over [HTTP MCP](http-memory-mcp.md).
