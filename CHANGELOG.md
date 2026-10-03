# Changelog

This file records changes to the LifeOS plugin for Hermes. Version numbers use
`MAJOR.MINOR.PATCH`. The [VERSION](VERSION) file records the current plugin version.
Keep it equal to the version in both plugin manifests.

## Unreleased

### Added

- A root `VERSION` file and version information in the README.
- This changelog and instructions for future version updates.

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
- The PR #1 corrections are not deployed to `.212`, `.211`, or `.213`. Earlier
  isolated `.212` browser acceptance has its own scope and limitations.
