# Changelog

This file records changes to the LifeOS plugin for Hermes. Version numbers use
`MAJOR.MINOR.PATCH`. The [VERSION](VERSION) file records the current plugin version.
Keep it equal to the version in both plugin manifests.

## Unreleased

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
