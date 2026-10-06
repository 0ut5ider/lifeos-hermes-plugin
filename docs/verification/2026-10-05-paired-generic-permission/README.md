# Paired permission request

Date: 2026-10-05. One case runs the native Safety hook on `PermissionRequest.1.1` with the pinned matcher `Write|Edit|MultiEdit|Bash`. Both clients run in their default permission mode and ask to run `touch pair-permission-marker`. Both clients pass.

| Effect | Result |
| --- | --- |
| Hook input names tool `Bash` and the exact command | Both clients. Claude Code also sends a `description` and permission suggestions. |
| `permission-decisions.jsonl` row with decision `neutral` and reason `default-defer` | Both clients, equal after normalization. |
| The command does not run, because no human can approve it in a non-interactive run | Both clients: the project directory stays empty. |

[permission-proof.json](permission-proof.json) recomputes the changed files from the raw captures and checks the empty project directory. The comparison method is the [generic file and output comparison](../2026-10-05-paired-generic-hooks/README.md).

## Attempt that stays open

A `ConfigChange.1.1` case wrote a new skill file. Claude Code in print mode emitted no ConfigChange event, so the case has no native control. The registration stays open.

The focused suite passes 115 tests. This case covers the deferred branch only. The cumulative ledger contains 100 equal selected cases for 55 registrations. Complete compatibility remains unverified.
