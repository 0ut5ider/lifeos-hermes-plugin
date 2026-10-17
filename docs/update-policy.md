# Update and recover a qualified integration

A supported release is a tested combination of Hermes, LifeOS, bridge, manager, dependencies, and dashboard. Update the complete combination through **LifeOS releases**. The [installation guide](installation-workflow.md) owns the shared preparation and apply instructions.

The [current release record](verification/2026-10-16-release-0.7.3/README.md) supplies the exact package identity. The ordered upstream revisions and patch lists are declared in [`install_source.py`](../lifeos_hook_bridge/install_source.py) and [`prepare_sources.py`](../scripts/prepare_sources.py).

## Owner update workflow

1. Finish or stop active work and retain a private recovery checkpoint.
2. Select **Update LifeOS** or **Update plugin** in **LifeOS releases**.
3. Leave the version empty for the latest stable package, or select an exact published version.
4. Wait for preparation, then select **Review release**.
5. Check the version, commit, hash, profile, and current owner authorization.
6. Select **Install this release**.
7. After restart, verify `hermes lifeos-release status IDENTIFIER` and `hermes lifeos-version`.
8. Check services, the configured model, messaging policy, and any enabled external memory connection before resuming normal work.

Both update buttons select the complete qualified package. The manager stages outside the active installation and checks the certificate, archive, selected programs, services, profile, and owner authority. It preserves current model choices, credentials, memory configuration, and user data.

Do not run `hermes update`, an upstream LifeOS updater, or a manual program overlay over the managed installation. Those operations can separate the patched host, native programs, bridge, and recorded package identity. A successful upstream checkout or clean patch application is not compatibility evidence.

## Recovery and rollback

Use the operation's actual current status. A queued worker is unfinished. `preparation_failed` leaves the previous programs selected. `recovery_required` needs the retained operation and a reviewed recovery action.

When available, the dashboard provides **Recover operation** and **Restore prior programs**. The command-line equivalents are:

```bash
hermes lifeos-release recover IDENTIFIER
hermes lifeos-release rollback IDENTIFIER
```

Rollback requires the current release identity, retained programs, and native mount to match the operation. Later program edits, a later remount, or another release can expire that rollback. Use the current `restore_available` result. Do not assume an older applied operation is still restorable.

If interruption stops the dashboard, use the retained qualified command from that operation. If the installed manager directory is missing, an operator must use the retained worker and verified journal. Do not recreate directories, edit the plan, or erase the operation to make a control reappear.

Recovery and rollback preserve current user data and refuse conflicting later edits. They restore selected software, not a historical personal-memory state. Review [provider return and software removal](memory-portability.md) as separate workflows.

Data-only profile backups exclude managed runtime workspaces. They do not establish full program recovery or external Atlas coverage. A whole-guest backup must include selected programs, native user data, external Atlas state, governance metadata, and pending journals as a coherent group. The [daily recovery contract](deployment/daily-text/README.md#final-daily-vm-backup-and-recovery-gate) defines that operator gate. Restore activated backups with networking removed and automatic application services masked before current owner and audience review.

## Qualify a new upstream combination

1. Select exact upstream commits and a bridge/manager program commit.
2. Prepare sources outside the running installation and port every required patch.
3. Compare registrations, program maps, dependencies, selected services, and owned mount files.
4. Run focused source tests and the affected native behavior controls.
5. Obtain independent review and resolve measured findings.
6. Build from committed source, then test the exact archive and record its integrity before and after execution.
7. Verify fresh installation, update, interruption recovery, rollback, and the changed installed workflows in isolated fixtures.
8. Publish the qualified immutable package and certificate.
9. Update development before daily, with current owner review and preservation checks.
10. Add deployment evidence without replacing initial release assets.

Test counts and inherited gates must name their package and environment. Record failures, skips, and process-inspection restrictions explicitly. Never replace failed receipts or claim a clean full run from coverage across separate environments.

The [contributor guide](../CONTRIBUTING.md#release-changes) identifies build inputs and evidence rules. The [historical update snapshot](history/2026-10-16-update-policy.md) retains earlier component transactions, shared-root constraints, and `.212` operator checks.
