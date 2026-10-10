# Daily text profile

The staged `PULSE.user.toml` selects Adrian's first daily Discord release. It uses local job output until the private channel passes delivery acceptance. The [configuration gate](../../verification/2026-10-08-daily-pulse-profile/README.md) verifies native resolution and job execution. Installed scheduling and release acceptance remain open. Adrian selects only the main Pulse dashboard. Do not start or expose the separate Telos application. The Telos skill template can remain in the native source package; it does not establish a separately accepted service.

Adrian selects private-channel setup after creation of the daily guest. Complete local application acceptance on `.252` first. Provision the separate daily guest, then create and verify its private Discord channel. Complete channel delivery and audience checks before bot cutover or lasting-memory activation on that guest. Keep `.252` as the development server.

Audio and video processing move to the later voice release. Do not start the Content media runner for this text release. Main Pulse retains the governed Content board and its admitted board actions. A native run request records intent; it does not establish working extraction, transcription, or production.

Use the actual Hermes dashboard for administration. The first-release profile disables the native Pulse Hermes core-file editor. Its legacy status and file routes do not have governed owner adapters. Adrian confirms this launch selection on October 10. It preserves the main Pulse personal dashboards and the governed gateway health readers. Do not enable the editor until its read and write routes pass current owner admission and publication checks.

Complete the governed Pulse editor in a later tested release. The [project to-do list](../../../TODO.md) retains its required read, write, remount, revocation, and recovery checks.

The operator deployment must perform these actions:

1. Back up the selected profile, native user configuration, and release manifest.
2. Verify the selected LifeOS root and its current local owner grant.
3. Verify that the installed Hermes command supports every selected owner job.
4. Install `PULSE.user.toml` into `LIFEOS/USER/CONFIG` within that selected root, with mode `0600`.
5. For a fresh store, install `CONDUIT.config.json` as `LIFEOS/USER/CONDUIT/config.json`, with mode `0600`.
6. Configure the daily guest timezone as `America/Toronto`.
7. Leave excluded notification credentials unset.
8. Verify the current configuration and policy binding before starting Pulse.
9. Test actual job execution, restart, and the selected private model routes.
10. Add governed Discord delivery after the private channel passes acceptance.

Run `hermes lifeos-job atlas-sync` after the local owner grant is accepted and before testing the Atlas dashboard. Check its capacity result and warnings. The daily profile repeats this governed command at 06:50, before the 07:00 morning brief. Dashboard regeneration runs the same sync before native narrative generation. An empty initialized graph stays idle and makes no narrative model request. Current-source edits become visible at the next scheduled sync or explicit dashboard regeneration. This release does not consume Atlas event hints or promise immediate refresh after every file edit.

Atlas has several independent bounds. The database limit is two MiB. Each Gear, Projects, snapshot, and narrative source is limited to 256 KiB. Complete graph admission also has a 10,000-text-field projection limit and a 2,048-row limit per table. Run and lifecycle history consume those limits even when current assets remain unchanged. The owner command reports counts, bytes, limits, and warnings at 80 percent capacity. This warning threshold is an operator choice. Over-limit plans refuse before replacing the live graph or snapshot. Raising the database bound alone does not address a lower projection limit.

Before adopting monitored refusal for daily use, verify the retained rebuild procedure in the acceptance installation. Drain all profile writer services, resolve pending owner recovery, and retain the database, snapshot, and narrative cache privately as one reviewed group. Run admitted sync against retained Gear and Projects sources to build the current derived graph. Keep the archive and its hashes. The current graph then has fresh history; prior history remains in the archive. Do not retain only the database or perform this operation while writers run. Do not rebuild an inventory whose current representation already exceeds capacity. That inventory needs a separately tested coordinated bound or representation change.

## Final daily VM backup and recovery gate

The existing native and profile backup formats do not include the external Atlas directory. A successful profile restore alone does not preserve Atlas history and does not complete this gate. The final daily VM must have a reviewed whole-guest backup that covers every group member below:

- The selected Hermes profile, ownership configuration, session database, and release manifest.
- Native USER_DATA, including Gear, Projects, narrative cache, and governance SQLite metadata.
- `memory.root.parent/.local/state/lifeos/atlas`, including `atlas.db`, `snapshot.json`, and event hints.
- Pending owner publication journals and any preserved recovery files.
- The selected program installation and its exact source and plugin manifests.

Complete these checks before bot cutover and lasting-memory activation:

1. Confirm that every selected path and disk belongs to the guest backup. Check mounted and excluded paths.
2. Drain all selected writer services and record exact hashes, private modes, source versions, graph identities, observations, run history, lifecycle events, and governance receipts from synthetic acceptance data.
3. Create and complete an off-server guest backup. Retain its archive identifier and coverage receipt.
4. Restore into an isolated VM with networking and automatic services disabled. Keep recovered ownership and sharing disabled until current account and Discord audience admission are accepted.
5. Verify SQLite integrity and the complete graph, snapshot, cache, sources, governance metadata, program manifests, and exact synthetic hashes.
6. Repeat the grouped backup and restore after an actual interrupted Atlas publication. Verify that normal owner recovery restores every original group member.
7. Repeat with a later owner edit. Verify that recovery refuses to replace any group member and retains the edit and journal.
8. Confirm the final daily VM's enabled off-server backup schedule and retention receipt.

The [synthetic grouped restore tests](../../../tests/test_memory_atlas_guest_recovery.py) verify coherent filesystem restoration, interrupted group recovery, and preservation of later edits. They do not establish Proxmox disk coverage or a final VM restore. Those installed checks remain mandatory after creating the daily VM.

Schedules use the guest's local timezone. Conduit capture runs every two minutes through the fixed owner command. The selected native adapter reads LifeOS work events from Hermes hook activity. App focus, Git, and GitHub capture remain disabled. The native adapter name `claudeSession` remains unchanged. Do not install a separate raw Conduit capture unit. The profile runs consolidation at 03:00, cleanup at 03:45, and the morning brief at 07:00. It retains the shipped cost aggregation and healthcheck schedules. It disables voice, GitHub Work, Cloudflare Synapse, Claude quota reporting, and the private Bunker integration. The public package omits the Bunker implementation. Siri remains loaded as infrastructure and refuses turns when its key is unset. The profile preserves the private FlashNext tier settings.

To reverse the configuration change, stop Pulse, restore the retained user configuration, verify its policy binding, and restart the verified previous release. Do not enable raw memory job commands while managed ownership is active.

The [October 9 capture schedule gate](../../verification/2026-10-08-remaining-reader-audit/README.md) passes 13 cases. Native scheduler spawning invokes the actual Hermes parser. A real Hermes file write triggers native ISASync, and capture consumes the actual work-event ledger. Events use mode `0600`, and repeat capture produces no duplicate. These results do not establish installed scheduling, restart, or Discord delivery.

The [installed daily acceptance](../../verification/2026-10-09-daily-release-installed/README.md) now verifies actual two-minute capture, all four selected owner commands, service restart, active native job interruption, and current profile reconstruction. The morning brief still contains shipped sample goals. Private-channel delivery and the combined release remain open.
