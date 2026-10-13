# LifeOS 0.4.1 qualification

The patch candidate corrects an actual public bootstrap failure.
Stock Hermes v0.21.7 checks `args.version` before it dispatches plugin commands.
The release manager also stores its exact release choice in that field.
Both separated and equals-form `--version` therefore print the Hermes version instead of preparing a release.
The fix uses `args.release_version` and preserves the external option spelling.
It adds no Hermes or LifeOS patch group and changes no dependency lock.

The real parent/subparser regression fails before correction and all seven command tests pass after correction.
The initial additional test invocation names a nonexistent dashboard module. Its loader error remains recorded.
The corrected focused checks use the actual module name.
The public root CLI failure and its output remain in the 0.4.0 evidence folder.
The published 0.4.0 assets stay immutable. The default latest path is verified separately.
The daily guest remains on exact 0.3.1. No personal data is imported or reset.
The corrected complete 0.4.1 package must pass review and qualification before publication or daily promotion.


The installed SDK also exceeds its ten-second registration limit when it inventories skill files.
The corrected bridge caches directory metadata once per skills root and replays each root in source order.
Two real configuration-role regression tests fail before the correction and pass after the correction.
The focused review is clear. The primary repeats its filesystem and configuration-change probes.

The corrected sealed candidate uses program commit `96f4f8fbef21f53ee704eb16f34698bc35b5dc77`.
Its archive SHA-256 is `462297fa0c20166ca77d0bf37fcef556b50832ff7bf46327d9777368ea80670e`.
It passes 631 integration tests and 716 official Hermes tests across 38 files.
Fresh installation and installed interruption recovery pass with actual process exit 73.
Normal installed update and automatic guest reboot pass on `.252`.

The protected backup is `PBS-01:backup/ct/101/2026-10-13T06:25:09Z`.
Its actual restore passes all three Atlas cases and verifies 143 program targets.
The controller disconnects the restored guest network and masks application services before its first boot.
The controller removes disposable guest 110 after verification. Existing guests 100, 101, 102, and 801 remain running.

The first backup fails after the PBS container stops. The container restarts and the repeated backup succeeds.
The first restore exceeds its 150 GiB disk quota because destination compression differs from source compression.
The repeated restore uses the same protected archive and a 300 GiB disposable disk. The repeated restore succeeds.
Both failed attempts remain in the evidence. Neither failure changes the product package.

The stop-mode backup restarts `.252` with a different DHCP address.
The recovery sets guest 101 to persistent `192.168.8.252/24`, with gateway `192.168.8.1`.
The source observer confirms the exact package and all three services after this change.
To undo this network change, restore the original `net0` value from `development-address-restoration.json` and reconfigure `eth0`.

Normal authenticated rollback restores exact 0.3.1, all three services, all three public aliases, and the selected model mapping.
The strict release certificate qualifies the complete 0.4.1 package. Public installation verification follows publication.

PR16 merges at `6c13407f33e5d7c2a982c1618b1a26dd0511f855`.
Release `v0.4.1` publishes the exact qualified assets as the latest stable release.
The 0.3.1 and 0.4.0 asset identities remain unchanged.
The GitHub tag endpoint returns 404 for the draft release. The authenticated release list supplies the draft verification record.
Public installation and development update acceptance follow this publication.

The public fresh installation passes explicit `--version 0.4.1` in 173.493 seconds.
It uses the actual public GitHub plugin, archive, and qualified certificate.
A read-only daily observer verifies exact 0.3.1 and all three running services.

The first default development operation is refused before publication.
Qualification rollback restores a development-era standalone manager.
That manager reviews 140 targets and omits all three public Hermes aliases.
The published worker requires 143 targets and refuses that reviewed plan.
The evidence preserves the refusal and the exact installed manager source differences.
The native Hermes plugin command installs the manager at the public release tag commit.
The dashboard restarts and loads the selected manager before a new public operation.
This repair changes no release asset and imports or resets no personal data.

The initial public output check incorrectly requires empty standard error for native plugin installation.
The measured output contains expected runtime preparation progress. The corrected check verifies those exact messages.
The browser evaluate call times out after 15 seconds while owner review continues on the server.
The completed browser result records HTTP 200. No duplicate review is submitted.
