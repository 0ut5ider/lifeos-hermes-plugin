# Changelog

## Unreleased

0.8.0-rc.1 installs LifeOS into the owner's existing Hermes installation instead of a separate managed runtime.

- Check the Hermes installation before any change: `hermes lifeos-release compatibility` and the releases page compare every target file with the qualified stock and patched hashes. Preparation runs this check before it downloads anything.
- Refuse a Hermes that runs another Python version than the release qualifies, and report a damaged `lifeos-host.json` as host drift that names the file.
- Show the changed and added Hermes files, the configuration keys LifeOS changes, the files an update changes or restores, and any known conflicts in the review.
- Download a small integration package (bridge, release manager, and patches) and the pinned LifeOS commit. Patch the existing Hermes checkout in place and keep the original files for removal.
- Publish all host changes through one journaled transaction. Stop and restart only the services that the host has, and offer a standard unit for a hand-started gateway or dashboard.
- Prove after restart that the gateway imports the installed checkout with the patched hooks. Each restarted service must run a new process and keep its enabled state, the patched hooks and middleware API must be present, and the memory provider must not change.
- Report host drift in `hermes lifeos-version`: a `host` block lists the patched Hermes files that changed since installation.
- Hold `hermes update` while LifeOS is installed.
- Record the configuration values that LifeOS changes. Removal restores them unless the owner changed them later.
- Remove an in-place installation: restore the original Hermes files, delete the added files, and keep memory, `.env` owner lines, and third-party plugins. Removal still works when the Hermes update hold is already gone.
- Move a managed 0.7.x installation to in-place, including its gateway unit, and restore it to the managed runtime on request.
- Refuse the move while a Hermes unit runs the managed runtime through a program other than the account commands in `~/.local/bin`. Point the unit at `~/.local/bin/hermes` first.
- Keep a private failure record for stopped memory workflows and failed fresh-agent probes.

## 0.7.3 (2026-10-16)

- Add contributor instructions and a codebase navigation guide.
- Separate current setup instructions from historical verification records.
- Share dashboard request helpers and test fixtures.
- Share hook command parsing and release launcher serialization.
- Remove unused imports and preserve public memory interfaces.

## 0.7.2 (2026-10-16)

- Load scoped styles for both LifeOS setup pages through their plugin manifests.
- Show visible buttons, distinct sections, field labels, and keyboard focus.
- Separate HTTP address, permissions, sign-in requests, and connected agents.
- Explain disabled approval controls and separate manual token submission from permission inputs.
- Organize release preparation, review, recovery, and memory ownership controls.
- Fit setup forms and model grids to desktop and phone widths.

## 0.7.1 (2026-10-16)

- Keep private Discord notifications from creating unverified foreground history before the first human turn.
- Preserve actual notification delivery and mirroring in admitted conversations.
- Preserve admitted direct-message mirrors and native mirrors after memory ownership returns to Hermes.
- Keep webhook mirror permission checks outside the gateway event loop.
- Include notification mirror files in native patch regeneration.
- Keep existing memory admission and compression checks unchanged.
- Close failed Discord audience responses before propagating their refusal.

## 0.7.0 (2026-10-16)

- Add an optional Streamable HTTP memory server to the LifeOS Bridge dashboard listener.
- Add owner controls for HTTPS configuration, OAuth consent, per-agent tokens, and revocation.
- Reuse native memory grants and check credentials during tool operations.
- Preserve credentials across program updates and refuse their use in a recovered installation.
- Document Tailscale Serve for private HTTPS access. Keep the optional SSH transport.

## 0.6.0 (2026-10-15)

- Add owner-reviewed import from Hermes memory and portable LifeOS bundles.
- Preserve source occurrences, original bytes, references, and import provenance.
- Require explicit item decisions and current owner, source, and destination checks.
- Export governed facts into a retained bundle and bounded Hermes memory files.
- Return to built-in Hermes through a reviewed service transition and recovery journal.
- Refuse stale return reviews and preserve later settings, grants, and memory edits.
- Add complete software removal after verified provider return and separate owner review.
- Select qualified stock Hermes and retain personal data, exports, and recovery records.
- Disable Discord during removal and retain password-authenticated standalone recovery.
- Bind stock runtime execution, retained recovery sources, and software ownership.
- Normalize the retained environment before removal review with the pinned Hermes formatter.
- Exclude portability runtime workspaces from data-only backups. Full guest backups retain them.
- Qualify the exact package with installed removal, interrupted recovery, and disconnected whole-guest restore.
- Verify the default GitHub manager installation, latest stable package, preserved model choices, and an actual model reply.

## 0.5.0 (2026-10-14)

- Verify omitted native program baseline entries against the exact accepted archive before release updates.
- Preserve later edits and refuse changed, missing, or redirected accepted archives.
- Compare observer completion state with native event timestamps and bound journal capture delay.

- Add authenticated owner reads for the 24 declared Pulse core files.
- Bind eligible saves to reviewed source references and private recoverable backups.
- Keep credentials sealed, generated files read-only, and registered facts under the memory correction tools.
- Govern native health, guard-log analysis, mount checks, and remount requests.
- Hide cached core files when the overview fails or a core request refuses current owner access.
- Preserve drafts for source conflicts and require fresh reads after owner access resumes.
- Verify the installed editor. Deploy the complete package to development and daily profiles after qualification.
- Preserve daily model tiers, native HOME, configuration, and lasting memory.
- Enable the daily governed editor after current owner source admission.
- Verify public installation from the default GitHub URL and complete updates through Update plugin.
- Qualify the exact package with 821 integration tests, 716 native tests, and actual recovery and development acceptance.
- Verify the protected final daily restore across 64,567 runtime artifacts, 221 selected targets, seven current owner outputs, and three Atlas cases.

## 0.4.3 (2026-10-14)

- Bind release launchers to the account that owns the selected Hermes profile.
- Preserve a separate native service HOME during release preparation, review, and installation.
- Refuse account aliases and shared-write directories before preparation creates files.
- Verify the exact package with 683 integration tests, 716 native tests, and 39 account checks.
- Verify actual update, rollback, interruption recovery, reboot, and disconnected guest restore.
- Deploy the complete package to development .252 and daily .253 with existing data and model settings preserved.
- Preserve all 45 prior published assets. Record automatic morning acceptance separately.

## 0.4.2 (2026-10-13)

- Add Install LifeOS, Update LifeOS, and Update plugin controls for complete qualified packages.
- Prepare dashboard requests in detached processes. Keep owner review before installation.
- Bind service operations to the configured and running Hermes profile.
- Share one preparation lease between command-line and dashboard requests.
- Recognize the exact bundled Hermes launcher and preserve effective systemd environment paths.
- Create private stage metadata without changing the caller's umask.
- Use a private worker mask for native profile files and backup artifacts.
- Keep Hermes v0.21.7, the pinned LifeOS revision, and all native dependency locks fixed.
- Qualify the exact package with 675 integration tests and 716 native tests.
- Verify public GitHub URL installation, both latest-stable update controls, and governed lasting memory.
- Verify an interactive Hermes update with command approval and dashboard owner review.
- Verify disconnected whole-guest recovery of 64,268 runtime artifacts and all three Atlas cases.
- Preserve all 41 historical release assets. Keep daily 0.3.1 unchanged.

## 0.4.2-rc.3 (2026-10-13 test prerelease)

- Create private runtime metadata in stage subprocesses. Preserve the caller's umask.

- Verify the configured and running dashboard profile before service drain and after restart.
- Recognize the exact pinned Hermes bundled launcher. Refuse unrelated inline programs.
- Preserve literal percent signs in the effective systemd environment. Refuse declared environment files.
- Use one preparation lease for command-line and dashboard requests. Refuse pending installation and recovery.
- Preserve all existing release assets. Keep production deployment outside this test qualification.

## 0.4.2-rc.2 (2026-10-13 test prerelease)

- Change the complete integration version to verify a numerical update through Hermes and both dashboard update controls.
- Keep the program behavior from the corrected 0.4.2-rc.1 candidate.

## 0.4.2-rc.1 (2026-10-13 test prerelease)

- Add Install LifeOS, Update LifeOS, and Update plugin controls to the LifeOS releases page.
- Prepare the complete qualified integration for both update actions. Keep owner review and installation approval separate.
- Run page-requested preparation in a detached process with a private profile lock.
- Refuse duplicate preparation and report interrupted preparation without selecting active programs.
- Prevent isolated stock Python from writing bytecode into qualified source trees during dashboard review.
- Prepare valid block YAML for native mounting while preserving configuration values.
- Block further preparation during installation or required recovery. Display each operation identifier.
- Detect interrupted preparation before the worker identity is published. Preserve active launch leases.
- Drain the managed stock dashboard during first installation through a separate worker service.
- Include missing inactive gateway and Pulse definitions in the reviewed program transaction.
- Validate generated units with the actual systemd parser. Refuse unsupported physical service paths before generation.
- Refuse historical first-install workers without the service interface. Keep the dashboard responsive during refusal.
- Bind extracted and native source manifests to the certificate-bound archive. Verify retained workers before admission.
- Preserve unchanged service files during program publication and keep one fresh-recovery lease namespace.
- Preserve the existing native baseline time during updates with unchanged native programs.
- Drain the native test log queue before removing its temporary home.
- Keep release 0.4.1 as the default stable release during isolated user-action acceptance.

## 0.4.1 (2026-10-13)

- Keep the plugin release choice in a separate argument field from the Hermes global version flag.
- Preserve the external `hermes lifeos-release prepare --version X.Y.Z` option.
- Use cached directory metadata for skill inventories during plugin loading. Preserve file-change signatures and source roles.
- Scan each skill root once and replay its entries in the original source order. Keep the native SDK load deadline active.
- Pin public plugin installation to the full release commit SHA required by stock Hermes.
- Preserve the published 0.4.0 and 0.3.1 release assets.

## 0.4.0 (2026-10-12)

Release qualification is recorded in the published release certificate.

- Pin Bun 1.4.3 with the upstream streaming-extraction fixes. Preserve all twelve native dependency locks.
- Prepare Hermes v0.21.7 at commit 71d34bad1045610252eda02ee79549436896e784.
- Use ten Hermes patch groups and twenty-five LifeOS patch groups.
- Verify complete Discord morning windows and the active Pulse schedule.
- Add the standalone LifeOS release manager for complete package preparation and coordinated updates.
- Keep the accepted 0.3.1 package on the daily server during qualification.
- Keep the dashboard responsive during release review and admission.
- Retain incomplete program copies before preparation retry.
- Migrate the private native configuration before the mount records output hashes.
- Exclude native boot outputs from the runtime source seal. Retain checks for changed and added code.
- Resume interrupted first installations and preserve user data added after interruption.
- Start detached workers through a portable process launch and reap finished workers.
- Migrate generated program configuration before its expected bytes are recorded.
- Update all native public command aliases with the selected runtime.
- Record release runtime exclusions in data-only profile backups. Preserve full guest backup coverage.
- Recover queued operations after a coordinator exits before launch recording. Preserve a successor grant when a stale worker refuses admission.
- Build the program plan with the qualified candidate before reporting ready. Refuse incomplete plans before service interruption.
- Hide expired native rollback and check current and retained programs before stopping services.
- Check retained native recovery copies before rollback admission and service interruption.
- Keep worker failure reporting and grant cleanup inside the execution lock.
- Preserve recovery retry after refusal. Check native targets and retained programs before recovery changes files or stops services.


This file records changes to the LifeOS plugin for Hermes. Version numbers use
`MAJOR.MINOR.PATCH`. The [VERSION](VERSION) file records the current plugin version.
Keep it equal to the version in both plugin manifests.

## Unreleased

## 0.3.1 (2026-10-12)

- Select only pending Conduit work for native capture. Preserve whole-ledger fingerprints and refusal of private pending events.
- Review pending work through `LIFEOS/MEMORY/STATE/work-events.jsonl#conduit-pending`. Bind approval to cursor, ledger bytes, and retirement state.

## 0.3.0 (2026-10-12)

- Report active and staged integration versions through `hermes lifeos-version`. Verify installed plugin hashes before reporting an exact release.
- Accept matching development and release-candidate version declarations. Record exact commit and package identities in private deployment receipts.

- Allow explicit owner review of Conduit cursor state after a forget operation. Preserve current-source signatures and private or retired text refusal.
- Archive Atlas history during governed synchronization while preserving observation references, collector timestamps, and cumulative run counts.
- Read verified archive rows through `hermes lifeos-atlas-history` with current owner admission and retired-text refusal.
- Recover archive files and the live graph as one publication group. Use smaller retained windows when planned output exceeds capacity.
- Refuse `MEDIA:`, `[[audio_as_voice]]`, and `[[as_document]]` directives in the daily text morning operator before delivery.
- Verify native goals, sparks, and next actions against actual attachment parsing. Deploy the tested operator correction on `.253`.

## 0.2.0 (2026-10-11)

This version identifies the daily Discord text release deployed on `192.168.8.253`.
Private-channel admission, inbound delivery, ownership activation, and cross-session lasting memory pass.
Three isolated off-server restores pass. A protected backup includes the activated configuration.
The newest activated archive has not received another isolated restore test.
Actual morning generation and Discord delivery pass. The first scheduled 07:00 execution remains unobserved.
See the [daily deployment record](docs/verification/2026-10-11-daily-guest/README.md).
Atlas initialization and fresh-store acceptance pass on the isolated development profile.
The independent PR7 review finds no blocking product defect. The review follow-up closes test subprocess pipes and repeats the focused checks.

- Start fresh personal sections without shipped example goals, health records, finances, gear, projects, or companies.
- Retain the exact personal templates outside the active user tree for fresh-store review. Preserve existing stores.
- Allow bounded owner-job source checks to complete under concurrent native requests. Keep current authority checks before job launch.
- Close fresh-worker test pipes and reject warnings from subprocess finalization in the review gate.

- Admit complete planned Atlas graphs and snapshots before publication. Refuse projection, row, and byte limits without replacing live artifacts.
- Report Atlas capacity dimensions and warnings at 80 percent of each selected limit.
- Synchronize Atlas daily at 06:50 through the current owner command. Refresh before dashboard narrative regeneration.
- Keep empty Atlas graphs idle and preserve current admission for failure diagnostics.
- Define the final daily VM backup gate for grouped Atlas state, sources, cache, governance receipts, and journals.

- Add the governed Atlas sync owner command for admitted Gear and Projects sources.
- Publish the native Atlas database and snapshot as one recoverable file group.
- Preserve native asset identity, incomplete observations, and targeted-run sweep rules.
- Keep Atlas insight recovery when source or destination changes occur after publication.
- Bind the Atlas planner directory before loading native code. Ignore inherited directory overrides.

- Select the main Pulse dashboard and defer audio and video processing with voice.
- Verify actual private-model memory write and search across separate installed Hermes sessions.
- Verify installed governed Content actions, current owner revocation, and authenticated native dashboard reads.
- Verify actual scheduled work-event capture and all four selected owner commands.
- Stop an active native owner job and clear all acceptance service groups.
- Recover the tested profile locally and from the completed Proxmox Backup Server archive.
- Disable the optional Pulse core-file editor under the confirmed first-release decision.
- Correct native Mount list indentation, Pulse shutdown waiting, and strict daemon types.
- Admit bounded owner-job output through its four MiB byte limit. Preserve reviewer limits and complete retirement filtering.
- Send complete Algorithm overview prompts through the shared inference function. Avoid Linux argument limits.
- Complete native Content action responses and display HTTP failures. Verify actual browser owner refusal and restoration.
- Recheck current owner authority between session learning writes, proposal cleanup writes, Knowledge record transitions, and queue deletion. Retain recovery after revocation.
- Keep unknown receipts and recovery journals when Algorithm, Conduit insight, or LocalIntelligence publication detects a later change after writing files.
- Verify every Algorithm summary, LocalIntelligence digest, and Conduit insight destination before committing its receipt. Preserve later destination edits and retain recovery for incomplete groups.
- Record the conditional Hermes upgrade that can remove one of the 36 functional patches after complete qualification.

The following changes also belong to this release:

- Preserve Discord command IDs during synchronization. Compare inherited settings without recreating unchanged commands.
- Release pending clarification waiters when the gateway interrupts their turn.
- Record Discord slash routing and dispatch without interaction tokens or option values.

- Recover an interrupted target mount before restoring the previous LifeOS selection and mounted files.
- Bind selection status and recovery to the invoking Hermes profile. Recheck the owner in the detached worker.
- Check completed target mount files before selection rollback. Preserve later owner edits and refuse service restart.
- Authorize interrupted selection recovery against its journal roots and current profile owner.
- Serialize selection admission and shared service changes across account profiles with an account lock.
- Validate the active native mount on every selection recovery attempt. Preserve edits after interrupted compensation.
- Permit selection retry after a confirmed stopped launch with no transaction journal. Keep uncertain workers pending.

- Verify actual private GitHub reminder delivery, concurrent repeat suppression, authentication refusal, and retry.

- Stamp global memory-review admission before starting detached inference. Preserve cadence across interrupted publication.
- Verify complete installed sessions, real external-data delivery, actual request interruption, and full dependency-tree update and restore.

- Publish native completion state and ISA pages atomically. Preserve prior files after interruption.
- Coordinate global review, capability audit, reminder routing, and work feedback state across concurrent hooks.
- Apply actual documentation corrections from complete model JSON to reviewed documentation targets.
- Require current source admission for response previews and accept native document metadata through its document validator.
- Exclude code and quoted directives from standing feedback instructions.
- Publish reminder delivery markers after confirmed command success.

- Save the native response cache only after completed Hermes generation. Preserve the prior cache after interrupted or rejected candidates.
- Retain real title-inference success and refusal controls, native startup branches, managed health admission, and isolated usage fetch evidence.

- Preserve learning identity across concurrent sessions and repeated capture days.
- Coordinate installed learning and cleanup programs during synchronous and detached execution.
- Preserve the prior version warning marker after interrupted native publication.
- Record requested child tiers and actual reasoning effort alongside selected and observed models.
- Verify actual private child effort and API gateway watchdog delivery.

- Correlate native child starts and stops with actual Hermes subagent callbacks.
- Record the observed response model separately from the selected child model.
- Coalesce current native clock context and discard stale asynchronous clock results.
- Apply the remote terminal guard to native ascent-state writes.
- Verify single and batch questions, finalization, child failure, and cancellation.

- Coordinate native post-hook state writes for parallel calls in one session.
- Verify detached audit rows after parent interruption and real task-board governance.

- Record ISA views after synchronization finishes its resume write.
- Render the latest observed ISA criterion detail in the system-change line.

- Apply MCP deny and ask rules before transport execution. Preserve managed policy precedence and malformed policy review.
- Publish concurrent evaluation fire state through separate temporary files. Preserve the evaluator's single-run lock.
- Verify actual batch and concurrent file evaluations with private model responses.
- Enable the batch patch schema for mounted private model profiles. Preserve explicit capability selections.
- Verify applied file effects and actual Write, Edit, and batch knowledge warning delivery.
- Include the protected instruction approval patch in Hermes patch regeneration.
- Deny unattended protected instruction writes before Hermes waits on an unavailable interactive approval queue.
- Honor the native Pulse hook switch before dispatching skill or agent policy requests.
- Detect shell-quoted literal system-write targets in the native Bash guard.
- Retain seven actual configuration evaluation pairs, including child inference and protected-file approval.
- Verify acceptance scenarios and artifact hashes in addition to selected registration cases.
- Isolate synthetic service fixtures from manager-wide unit enablement changes.

- Record the served model for inherited agent calls before the Hermes transcript write. Preserve explicit tier selection.
- Normalize question batches and record synchronous delegation when background delivery is unavailable.
- Audit the actual configuration source and path with separate source baselines.
- Classify successful web extraction from structured results, including null errors and partial success.
- Retain eleven further selected hook controls. All 74 registrations now have a selected passing case.
- Separate actual native client events from direct native web and batch handler comparisons.
- Include the web-result classifier in patch regeneration and verify complete source reconstruction.

### Changed

- SSH memory sharing enrollment moves to the separately installed `optional/lifeos-memory-sharing` component.
  The plugin package no longer changes the SSH authorized keys file, and the Hermes install scan is clean.
  Operators who use SSH sharing must run the component installer after this update.

### Added

- Private native data backups with SQLite governance metadata and integrity checks.
- Hermes commands to create and inspect native data backups in the selected profile.
- Native backup recovery into a separate private tree with verified references.
  Preserve the original store and keep recovered ownership inactive.
- A root `VERSION` file and version information in the README.
- This changelog and instructions for future version updates.
- A registration effect matrix and a completion check for retained hook evidence.
- Paired ToolSearch Safety and StopFailure audit controls on disposable profiles.
- Nine paired lifecycle effect cases through real Claude Code and Hermes events,
  with exact synthetic file captures and assertions checked by the evidence gate.
- Six further paired lifecycle cases for repair containment, terminal persistence,
  memory-health reporting, and documentation inventory. Twelve real CLI runs pass.
- Eight paired startup cases cover context readback, advisory markers, and terminal
  gates. Seven have equal effects. The remote terminal isolation difference remains explicit.
- Three paired request-delivery cases verify selected startup content inside real
  model requests. The loopback endpoint returns the expected authentication failure.
- Three paired startup response cases verify context selection and successful
  private FlashNext replies. All six final client runs pass.
- Three paired response-cache cases verify creation, replacement, and the exact
  2,000-character limit through real Stop events. All six client runs pass.
- Five paired feedback cases verify explicit and bare ratings, praise, neutral
  numeric text, and low-rating learning. All ten final client runs pass.
- Five paired format-contract cases verify turn state, measured violations, depth
  requests, stale-cache exclusion, and model delivery. All ten client runs pass.
- Five further feedback cases verify normal completion with the pinned asynchronous
  registration and timeout. All ten client runs pass.
- A full-experience release plan with private FlashNext tiers and Discord voice
  input and spoken replies. Voice follows the core functionality.

### Fixed

- Make serialized WAL-mode backups readable as standalone SQLite snapshots.
  Preserve the live database journal mode and committed facts.
- Recover missing child admission after an interrupted native compression handoff.
  Require verified native lineage and unchanged parent authority.
- Preserve user whitespace in Hermes model requests so input proofs remain exact.
- Preserve verified memory authority when compression rotates a conversation.
  Require recorded lineage and unchanged authority before the caller adopts the child.
- Let auxiliary admission adopt an unchanged context's published input proof.
  Continue to refuse retired generated content and stale fact generations.
- Resume verified conversations after a native correction or forget operation.
  Require foreground history repair before auxiliary calls can continue.
- Refuse history refresh after an applied identity proposal. Bind its recorded
  state separately from fact retirements.
- Repair readable Responses history after a native correction or forget operation.
  Preserve protocol identifiers, current user quotes, and stored transcripts.

- Hermes catalog search results run the existing result transform and augmentation
  callbacks. LifeOS Safety context reaches the tool caller.

The [October 4 deployment](docs/verification/2026-10-04-catalog-release-212/README.md)
installs the catalog fix on both active `.212` profiles at tested commit
`02d7ac8`. The plugin still declares version `0.1.0`; the exact commit records
this test deployment. Complete hook compatibility remains unverified.

## 0.1.0 (2026-10-03)

This entry records the experimental repository baseline after
[PR #1](https://github.com/0ut5ider/lifeos-hermes-plugin/pull/1) merged.
The date records the merge. Both plugin manifests already declare `0.1.0`.

### Added

- A bridge from native LifeOS hooks to Hermes lifecycle events, including command
  checks, approval handling, context injection, and final-answer checks.
- A LifeOS Bridge dashboard with model and effort settings for Haiku, Sonnet,
  Opus, and Fable, plus a configurable Stop hook limit.
- Source preparation with nine Hermes patch groups and ten LifeOS patches for
  the tested compatibility set.
- Fresh installation, authenticated mounting, staged updates, version restore,
  and recovery controls with durable transaction journals.
- Experimental native memory operations, reviewed source adoption, proposal
  decisions, correction and forget handling, and authenticated reader routes.
- An optional Model Context Protocol (MCP) memory service and SSH enrollment.
- An external development recorder, hook comparison evidence, and installation,
  Discord setup, update, and removal guides.

### Fixed

- Apply and restore record recovery intent before stopping the gateway. Recovery
  before a file swap restarts the current program and preserves later user data
  and profile changes.
- Dashboard worker status reflects completed durable transactions after a worker
  exits unexpectedly.
- Memory admission and retrieval exclude private and forgotten filename labels.
  Rejected-source and proposal diagnostics also exclude those labels.
- Version restore protects later Hermes profile edits and supports separate
  filesystems for profile and baseline snapshots.
- Direct child prompt checks cover the complete prompt. Private recorder output
  filters environment values outside its diagnostic allowlist.

### Verification

The [final PR #1 correction gate](docs/verification/2026-10-02-sol-review-fixes/README.md)
records 1,041 passing Python cases and 21 environment-dependent skips, plus
32 passing recorder cases and 12 passing dashboard cases. These results apply
to runtime revision `2c02dc5`; subsequent changes before the merge contain
documentation only. This entry summarizes that existing evidence.

### Known limits

- The plugin remains experimental. Complete Claude Code hook parity is unverified.
- Lasting-memory ownership and external sharing remain disabled on running
  installations. The full memory activation gate is incomplete.
- Existing-memory import is planned and unimplemented.
- The recorded local correction gate does not establish compatibility with newer
  upstream revisions or complete Docker and remote workspace behavior.
- The October 3 release deploys the PR #1 corrections to both active `.212`
  profiles. The `.211` and `.213` installations remain unchanged.
