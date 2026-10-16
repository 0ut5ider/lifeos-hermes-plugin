# Documentation

Start with the task you need to complete. Active guides describe the supported integration. Dated records preserve the state observed at their checkpoint.

## Use the integration

| Task | Guide |
| --- | --- |
| Install the complete package from the Hermes dashboard or a conversation | [Installation workflow](installation-workflow.md) |
| Update, recover, or roll back a qualified release | [Update policy](update-policy.md) |
| Configure model tiers, Stop hooks, or trusted remote projects | [Configuration](configuration.md) |
| Connect external agents over HTTPS | [HTTP memory MCP](http-memory-mcp.md) |
| Configure a private Discord text channel | [Discord setup](discord-setup.md) |
| Import, export, return to Hermes, or remove integration software | [Memory portability](memory-portability.md) |
| Check source version or deferred work | [Changelog](../CHANGELOG.md), [TODO](../TODO.md) |

## Work on the code

| Task | Guide |
| --- | --- |
| Start a contribution or run focused checks | [Contributing](../CONTRIBUTING.md) |
| Find implementation entry points and their tests | [Codebase map](codebase.md) |
| Prepare pinned upstream sources for isolated testing | [Source preparation](clean-install.md) |
| Understand patch ownership and regeneration | [Patch footprint](patch-footprint.md) |
| Understand hook translation and accepted scenarios | [Hook parity](hook-parity.md), [Step 1 acceptance](parity/step1-acceptance.md) |
| Capture private development traces | [Recorder guide](../development/README.md) |
| Understand potential upstream contributions | [Upstream proposals](upstream-hermes-proposals.md) |

## Check a release claim

The [0.7.2 record](verification/2026-10-16-release-0.7.2/README.md) is the current qualified release reference. It links the initial certificate, archive identity, independent review, installed verification, and deployment receipt. The [verification index](verification/README.md) identifies earlier release milestones and explains evidence limits.

A dated `PROGRESS.json`, candidate report, or test count describes that checkpoint. It cannot establish the current installed version. Use the installed `hermes lifeos-version` result and the matching deployment record. Keep release assets and original receipts immutable.

## Historical design and implementation

These pages retain decisions and implementation details. Their old host addresses, “current” labels, and open gates do not override active guides or later release records.

- [Full experience plan](full-experience-release-plan.md)
- [Memory implementation and activation gates](memory-implementation-plan.md)
- [Memory import design](memory-import-plan.md)
- [Fresh-store selection design](fresh-store-selection.md)
- [Parity resolution plan](parity-resolution-plan.md)
- [VersionDrift baseline design](version-drift-baseline.md) and [review design](version-drift-design.md)
- [Earlier test environments](test-environment.md) and [browser acceptance fixture](browser-acceptance-212.md)
- [Claude reference fixture](claude-reference.md) and [source comparison limits](parity/source-differences.md)
- [Daily deployment profile and recovery contract](deployment/daily-text/README.md)
- [Dated guide snapshots](history/README.md)
- [Engineering notes](../notes/README.md)
- [Independent agent reports](agents/README.md)

The daily deployment profile contains a local operator configuration and is also a package input. It is not a generic installation template for another owner.

## Maintain these documents

Keep one active guide for each user task. Link to that guide instead of copying its steps into the README, TODO, or release record. Keep the README focused on product scope and entry points. Keep unfinished product work in TODO. Put measured results in dated verification records and reasoning in notes.

When changing a guide, check its relative links and heading anchors. If a historical section moves, preserve its record and provide a current destination. Do not rewrite an old failure as a passing result or mark a queued operation complete.
