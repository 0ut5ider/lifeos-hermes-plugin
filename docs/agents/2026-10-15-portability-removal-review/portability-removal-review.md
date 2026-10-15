# Complete LifeOS removal inventory and implementation review

Date: 2026-10-15.
Role: Independent removal design reviewer.
Question: Which owned changes must a managed profile reverse to run stock Hermes, with personal data and later edits retained?
Model: gpt-6.1-sol, high reasoning effort.

## Conclusion

Implement removal as a new current-state transaction after verified reverse export and provider return. Prepare an exact qualified unpatched Hermes runtime and select it through verified launchers. Do not reverse the ten Hermes patches in place. Do not replay an older release restore journal or an ownership backup over current configuration.

The existing primitives cover owner authentication, file publication, fingerprints, writer draining, and interrupted transaction recovery. They do not implement complete removal. Two constraints need explicit treatment: the program launchers and Pulse service are account-wide, and the current `ProfileServices.resume()` requires the original service definitions and restarts Pulse. A stock Hermes runtime also loses patched Discord channel-only enforcement. Preserved configuration does not prove equivalent admission behavior.

This review inspected source only. It did not run removal, change products, access remote hosts, or read personal data. The copied source and SHA-256 identities are in `source/` and `source-identities.json`. The qualified 0.5.0 native mount source is saved separately as `qualified-Mount.ts`. No passing integration or release gate is claimed.

## Supported first implementation

Support the current managed complete-release layout when the active bridge, release manager, native mounted outputs, launchers, and unit definitions have a current verifiable identity. Preserve later unrelated configuration edits through semantic field changes against the current configuration. Present conflicts for changed integration-owned fields.

A release identity that verifies only bridge files is insufficient to authorize removal of the rest of the system. `release_version.status()` declares its `verification_scope` as `plugin_sources`. Validate the actual manager tree, runtime, mount outputs, and service files independently. See [release identity](../../../lifeos_hook_bridge/release_version.py:75), [current release admission](../../../optional/lifeos_release_manager/release_plan.py:18), and [program fingerprints](../../../optional/lifeos_release_manager/release_programs.py:45).

For arbitrary edited or shared installations, stop before publication unless the owner reviews a complete verified replacement. Do not attempt best-effort source patch reversal. Do not delete an account-wide runtime used by another profile. A refusal is a supported safe result; it is not successful removal.

## Owned surface inventory

The paths below are relative to the authenticated selected profile or its verified account home. Inspect actual journal targets instead of assuming the daily server layout.

| Surface | Current authoring path | Removal action |
| --- | --- | --- |
| `plugins/lifeos-hook-bridge/` | Complete release `_program_plan()` | Move the verified tree to private retained software recovery storage. Remove it from active plugin discovery. |
| `plugins/lifeos-release-manager/` | Complete release `_program_plan()` | Remove from discovery after a detached independent worker has all its code and authority. Preserve recovery code privately. |
| `plugins/lifeos/` | Native mount emits `__init__.py`, `guard.py`, `plugin.yaml`, `policy.json` | Remove exact owned files. Refuse a changed file or additional unreviewed plugin file. Remove the directory only if empty. |
| `config.yaml` plugin selections | Release worker adds bridge/manager enabled entries; native mount adds `lifeos` | Remove these integration names and owned entries. Preserve unrelated plugin lists, entries, comments, credentials, and models. Conflicts require review. |
| `config.yaml` memory selection | Ownership enables `lifeos-hook-bridge`, disables built-in stores | Select the already reviewed exported built-in memory configuration. Enable the stores that the export review selects. Remove the now-unused custom provider key when the stock schema requires it. |
| `config.yaml` skills | Native mount points `skills.external_dirs` to native `skills` | Remove only the selected LifeOS directory. Restore a known prior value only when its provenance is verified. Preserve later unrelated directories. |
| `config.yaml` context and approval settings | Native mount sets `context_file_max_chars`, approval deny rules, and bridge sets `file_tools.patch_format` when absent | Review exact owned values. Restore verified prior values or supported stock values only with explicit review. Preserve later custom values or hold removal for conflict. |
| `SOUL.md` | Native governed prompt mount | Remove the active LifeOS-generated prompt or replace it with a reviewed stock prompt. Preserve the current and verified prior bytes privately. Refuse to overwrite a later manual edit. Do not restore an earlier personal prompt without review. |
| `.env` | Native mount appends `HERMES_WRITE_SAFE_ROOT` when absent | Remove only an exact owned variable and associated owned comment block. Preserve every unrelated line and credential. A pre-existing variable is not owned by the integration. |
| `lifeos-memory.json` | Owner binding and memory provider configuration | Retain privately in the recovery bundle. Remove it from active integration discovery after stock selection. Do not alter the retained LifeOS store to disable it. |
| `lifeos-installation.json` | Profile LifeOS home/workspace selection | Retain privately, remove the active setting. Do not delete the selected home or workspace. |
| `integration-release.json`, `integration-candidate.json` | Managed release identity files | Retain with the removal receipt. Stop presenting the complete integration as installed. Preserve unrelated candidates unless they are verified integration state. |
| `~/.local/bin/hermes`, `hermes-agent`, `hermes-acp` | Managed release swaps these to operation runtime commands | Publish wrappers to the qualified stock runtime. Verify all three commands. Preserve the previous wrappers in the removal journal. Check all account profiles first. |
| Other reviewed Hermes launcher paths | Current service launchers are added to the program plan | Replace only proven owned launchers, after checking other consumers. Do not assume `~/.local/bin/hermes` is the only launcher. |
| `~/.local/bin/bun` | Release manager publishes qualified Bun binary | Remove or restore only when ownership and exclusive use are proved. A shared user Bun installation must remain. Retain the integration-owned copy with recovery artifacts if necessary. |
| `hermes-gateway.service`, `hermes-dashboard.service` | Existing or integration-created service units | Keep the services and bind them to stock Hermes. Replace only owned unit parts. The dashboard working directory must remain valid after software removal. Preserve unrelated environment, ports, authentication, and configuration. |
| `com.lifeos.pulse.service` | Native background service | Stop and disable it. Remove only an owned unit or retain an unrelated unit with an explicit refusal to claim complete removal. Restore the prior enabled state on rollback. |
| `com.lifeos.pulse.service.d/lifeos-installation.conf` | Selection worker sets Pulse working directory and `HOME` | Remove only the verified owned drop-in. Preserve any other drop-ins. Run daemon reload after changing definitions. |
| Native hooks and native program tree | Native `settings.json`, installed `.claude/LIFEOS`, tools and dependencies | Stop all carriers before detaching. For exclusively owned software, remove or move exact program files to private recovery storage. Never recursively delete the native root because it can contain data and unrelated hooks. |
| Source stores, user data, history, audit, workspace, exports, backups | Existing personal and recovery roots | Retain. Complete software removal does not mean personal-data erasure. |

Exact producer sources: [release program plan](../../../optional/lifeos_release_manager/release_worker.py:172), [release config edit](../../../optional/lifeos_release_manager/release_worker.py:136), [mount file list](../../../lifeos_hook_bridge/mount_transaction.py:20), [selection setting](../../../lifeos_hook_bridge/lifeos_installation.py:11), [Pulse drop-in](../../../lifeos_hook_bridge/selection_worker.py:55), [ownership edit](../../../lifeos_hook_bridge/memory_ownership.py:128), and [exact owned-hook replacement](../../../lifeos_hook_bridge/update_hooks.py:47).

The qualified native Mount source confirms configuration fields `context_file_max_chars`, `skills.external_dirs`, `approvals`, plugin enablement, generated `SOUL.md`, and `HERMES_WRITE_SAFE_ROOT`. Its exact inspected source is [qualified-Mount.ts](qualified-Mount.ts:267). A historical mount journal has seven profile outputs and sometimes a baseline output. Its retained prior state represents the previous mount, not necessarily the initial stock installation. Therefore `restore_completed()` alone cannot establish stock configuration after several mounts.

## Smallest safe orchestration

1. Create a private removal operation outside every active plugin and native program target. Bind it to the authenticated dashboard owner, selected profile, current native root and physical identities, stock source identity, export receipt, and exact target fingerprints. Keep the previous software and configuration in the same recovery journal.
2. Prepare the unpatched runtime before disruption. Use a pinned upstream commit with authenticated archive and exact source file map, frozen dependencies, and a matching compiled dashboard. The prior release already has a real stock-source proof at commit `71d34bad1045610252eda02ee79549436896e784`; do not infer that a newer stock version is qualified. A new package can include or authenticate this stock source and its runtime build inputs.
3. Use the installation lock and exclusive program lock. Check account-wide consumers and pending jobs. For the first implementation, refuse another named profile or service that uses shared launchers, Pulse, or the selected native program tree. This avoids adding broad account migration logic. If shared multi-profile removal is required, use a separate account-wide coordinator and qualify it explicitly.
4. Acquire the service barrier through the current reviewed definitions. Stop gateway, Pulse, and dashboard. Verify their control groups are empty and that no admitted CLI/dashboard/update/selection task can write. Program-lock cooperation covers running bridge turns; stock CLI and unrelated external writers need explicit admission or refusal.
5. Revalidate the export, source currentness, built-in destination, current configuration, service definitions, and all targets after the barrier. Publish a current-state semantic config transformation, owned plugin removals, stock wrappers, and exact retained exports with one durable journal. Recheck targets immediately before each mutation.
6. Publish and verify the desired service definitions and enabled states, then daemon-reload. Keep Pulse disabled. Resume only Hermes dashboard and gateway when their pre-operation states or explicit reviewed desired states require it. Verify the post-removal runtime independently.
7. Start a fresh actual Hermes conversation. Require built-in recall of the selected exported fact, no bridge hooks/providers/tools/prompts, stock source identity, and no LifeOS service execution. Publish the final safe receipt after these checks. Leave a standalone recovery command because the plugin that previously exposed recovery is now absent.

Existing building blocks: [owner setup lock](../../../lifeos_hook_bridge/ownership_setup.py:51), [program transaction](../../../optional/lifeos_release_manager/release_programs.py:173), [native authorization](../../../lifeos_hook_bridge/memory_administration.py:118), [service drain and empty cgroup verification](../../../lifeos_hook_bridge/profile_services.py:179), [installation lock](../../../lifeos_hook_bridge/installation_lock.py:56), [program lock](../../../lifeos_hook_bridge/program_lock.py:55), [runtime assembly](../../../optional/lifeos_release_manager/release_payload.py:7), and [stock source proof](../../../docs/verification/2026-10-14-release-0.5.0/verify_public_stock_source.py:7).

The existing `ProgramTransaction` supports deletion through `source=None` for both file and directory targets and retains directory before-images. Reuse this primitive with a new removal plan, not the last update's historical before-images. It verifies current artifacts and retained backups on recovery. Its ignored bytecode is acceptable only when active plugin directories no longer exist or cannot be discovered; a disabled stale plugin directory is weaker than actual removal.

## Measured design gaps and traps

1. `ProfileServices.resume()` verifies original definition hashes and starts original roles, including Pulse. After a verified drop-in or unit removal it refuses the changed definitions. A removal-specific desired-state service controller must separately bind original and final definitions. Do not weaken existing strict checks to make removal work. See [resume](../../../lifeos_hook_bridge/profile_services.py:277).
2. `OwnershipTransaction.rollback()` restores exact historical `config.yaml` and `lifeos-memory.json` and refuses later edits. This is correct recovery behavior but unsuitable for a current semantic provider return. Current model and dashboard edits must survive. See [rollback](../../../lifeos_hook_bridge/memory_ownership.py:212).
3. Per-profile installation/program locks do not serialize account-wide launcher and Pulse changes against another profile. The account selection coordinator exists for installation selection, but managed release admission currently holds per-profile locks. Use a strict supported-layout refusal until broader coordination is implemented and tested.
4. Channel-only Discord admission is a Hermes patch. The patch adds `guild_channel_only`, direct-message refusal, slash checks, and outbound destination checks. Stock source can preserve the YAML while losing these checks. Establish a stock-supported equivalent and test it, or make removal explicitly disable Discord and report that consequence for owner review. Do not carry personal-memory access into a wider audience by accident. See [policy additions](../../../lifeos_hook_bridge/patches/hermes-session-lifecycle.patch:706) and [acceptance cases](../../../lifeos_hook_bridge/patches/hermes-session-lifecycle.patch:1376).
5. Native program directories contain retained data, symlinks, caches, and background job definitions. Verify a public software file map, then move only exclusive program groups. Stopping Pulse retains jobs without executing them. A separate explicit review is needed if the owner wants equivalent Hermes-native jobs. Do not copy job commands blindly.
6. Removal cannot depend on authentication state only stored in code being removed. Admit a short-lived exact operation grant before detaching. Keep its principal/profile binding and revoke it after completion or explicit cancellation. Recovery must work after a process crash without silently widening the grant.
7. A complete integration can be removed from active use while recovery archives retain copies of its software. State this in the receipt. The data-preservation contract prohibits deleting archives and user stores merely to make a filesystem search return no LifeOS strings.

## Acceptance cases

These are required tests, not results from this review.

1. Real managed install, import current synthetic facts, create new facts, export, return, and remove through the authenticated UI. Verify built-in recall in a fresh real model session and actual gateway restart.
2. Verify exact stock commit and full source map, zero integration patches, correct frozen dependencies, all three command wrappers, and dashboard compiled files. Reject a single changed source or archive byte before disruption.
3. Verify active plugin inventory contains none of `lifeos`, `lifeos-hook-bridge`, and `lifeos-release-manager`. Verify no active external LifeOS skills, generated LifeOS prompt, provider registration, middleware, or bridge tools.
4. Snapshot user-store content and references, history, workspace, model settings, unrelated environment lines, dashboard authentication, and unrelated plugins before removal. Verify exact preservation afterward. Verify authorized Hermes memory changes separately.
5. Verify Pulse stopped, disabled, and cannot restart after user-manager restart or guest reboot. Verify unrelated timers and jobs remain unchanged. Verify no substitute Discord send occurs.
6. Fail each boundary after drain, each file/directory publication, launcher selection, daemon reload, service restart, and fresh-session verification. Resume or rollback from the private journal. Require no lost export, no stale mixed runtime, and no duplicate operation on retry.
7. Insert later edits to a plugin file, unit, owned drop-in, SOUL, config owned key, export destination, and launcher. Require a precise conflict without overwriting the edit. An unrelated config/model edit must survive the semantic plan.
8. Add another named profile, running CLI, foreground dashboard, shared launcher consumer, shared native root, or unrelated Bun user. Require explicit refusal or prove an independently qualified shared-consumer path.
9. Demonstrate missing/truncated before-image, symlink/hard-link/path substitution, changed UID or permissions, invalid owner grant, revoked owner, wrong profile, expired admission, and concurrent apply all fail closed with recoverable state.
10. Exercise stock Discord admission for the private channel, another guild channel, direct message, slash command, outbound text, and outbound file. If equivalent policy is unavailable, verify the reviewed Discord disablement and preserved credentials without sending anything.
11. Verify a fresh login sees the final stock state after the manager is gone. Verify standalone recovery can restore the complete previously selected integration after a failed removal. Verify repeated successful removal is idempotent.
12. Test both layouts: an existing stock dashboard augmented by the integration, and a dedicated managed daily account. Do not advertise arbitrary install removal from only one successful fixture.

## Recommended decision

Implement the current-managed-layout path first with a pinned stock runtime and explicit refusal for shared or unverified ownership. Keep import/export and provider return independently usable. Make the complete-removal option depend on all its additional source, service, audience, and ownership checks. Do not mark a provider return as complete software removal.
