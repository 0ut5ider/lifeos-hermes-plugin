# Patch footprint and plugin ownership

The bundle uses eleven Hermes patch groups and sixteen LifeOS patches. It targets the exact source revisions in `lifeos_hook_bridge/install_source.py`. A supported update must pass source preparation and behavior checks before installation.

## Hermes patch groups

| Patch | Responsibility |
|---|---|
| `hermes-plugin-events.patch` | Required policy dispatch, tool events, and result composition |
| `hermes-turn-gates.patch` | Prompt admission, final-answer gates, turn outcomes, and effective route facts |
| `hermes-command-policy.patch` | Command decisions, replacements, review scope, nested execution, and denial precedence |
| `hermes-session-lifecycle.patch` | Session start, resume, clear, and end events |
| `hermes-child-routing.patch` | Independent provider, model, and effort for each child |
| `hermes-strict-inference.patch` | Selected-provider inference without provider fallback |
| `hermes-remote-files.patch` | Remote whole-file stale-write protection |
| `hermes-cron-bootstrap.patch` | Installation-bound scheduled worker startup |
| `hermes-required-middleware.patch` | Required admission before model requests, exact user text, and rejection of asynchronous required callbacks |
| `hermes-web-result-status.patch` | External Safety delivery after successful and partial web extraction |
| `hermes-protected-instruction-approval.patch` | Immediate refusal of unattended protected instruction writes |

The additional native patches bind configuration audit rows to their actual source, detect shell-quoted literal write targets, honor the Pulse hook switch, and publish concurrent evaluation state through separate temporary files. The system-surface patch retains the latest observed criterion detail in the visible system line. The full declared order is in `scripts/prepare_sources.py`.

The groups replace the earlier 20-patch development sequence. Each changed file belongs to one group. Required callback registration belongs to the plugin-event group, and actual turn-route metadata belongs to the turn-gate group. The required-middleware group supplies model-request admission and its tests. It does not remove the required host behavior.

The redundant hook lookup helper is removed. Hermes's stock source launcher remains unchanged. The plugin registers `hermes lifeos-infer`, `hermes lifeos-probe`, and `hermes lifeos-backup` through the existing command API. These commands register before LifeOS is installed. Backup execution requires the selected profile's private memory configuration and an available native store.

## LifeOS model observations

The plugin resolves the configured model tiers. The native ModelRungGuard receives a small observation with the real provider, model, effort, resolved tier, and configured pin. The native hook validates the observation and keeps its own warning policy and audit log.

The plugin reads the last main assistant message. It excludes child sidechain rows. It recomputes classification from the current configuration on each prompt. Provider, model, and effort must match an explicitly configured route. Unclassified routes remain unknown. Identical Opus and Fable routes select Fable, which is the highest matching tier.

Native Claude aliases retain their existing interpretation. The exported `liveModel()` transcript reader remains available. The integration does not rename a local model to a Claude model.

## Verified task capability

Source preparation adds `hooks/lifeos-bridge-capabilities.json` to the LifeOS installation payload. The record names the tested source revision, the supported task-count contract, and the SHA-256 digest of the patched TaskGovernance file. The plugin has the same expected record.

The LifeOS installer copies the record with the hook files. The update transaction stages the record with the system files. Restore removes or restores the record with the prior hook files.

The plugin finds native registrations in the main settings and trusted local project settings. Remote project hooks keep their separate opt-in runner. The local capability record does not certify remote hook files.

The plugin verifies the record and native file bytes before using the externally supplied session count. Capability discovery does not execute a hook or send a TaskCreated event. Actual task creation still executes the registered hooks.

If a registered native TaskGovernance file has no valid record or its bytes change, the plugin stops task creation. The message requests an installation repair or update. The plugin does not silently replace the native policy with its own policy.

An existing installation needs the complete plugin and LifeOS update package. Updating only the plugin does not provide the capability record. Keep the prior snapshot until verification passes. The reduced profile for an unpatched Hermes installation remains a separate, documented installation choice.

## Verification and limits

The replay check compares the regenerated bundle with the intended modified source files. The behavioral checks cover native model warnings, task counts, update and restore, required policy failures, and command routing through a stock launcher.

The local plugin suite passes 347 tests, with 51 environment-dependent skips. The focused Hermes suite passes 163 tests, with the live SSH case skipped. See the [raw verification logs](verification/2026-09-29-patch-footprint/). The unchanged stock launcher suite passes 21 tests, with nine Windows-only tests skipped on Linux. The supplementary native permission case passes with the real Tirith scanner. These counts cover this reduction, not the full parity release gate.

The [independent Astra review](agents/2026-09-29-footprint-review/footprint-review.md) found one project-settings regression. The corrected implementation and regression tests passed the review rerun. No confirmed findings remain open.

The command fixture uses real HTTP requests against a deterministic local protocol server. It checks profile isolation, managed dependencies, image input, streamed child responses, and provider failure without fallback. It does not establish private model accuracy or reasoning depth.

This reduction does not complete the 74-hook parity release gate. The running `.212` gateway still uses its earlier package until a coordinated release is applied. The work does not deploy to `.211` or `.213`.

## Regenerate the Hermes patch groups

1. Prepare a source tree at the supported Hermes base revision.
2. Apply the intended changes to that tree.
3. Mark new files with Git intent-to-add so the diff includes them.
4. Run `python -m scripts.rebuild_hermes_patches --source PATH --output PATH` from this repository.
5. Copy the generated patches into both distribution directories.
6. Prepare a fresh source tree and compare its files with the intended tree.
7. Run the behavior tests before installation.
