# Daily text profile

The staged `PULSE.user.toml` selects Adrian's first daily Discord release. It uses local job output until the private channel passes delivery acceptance. The [configuration gate](../../verification/2026-10-08-daily-pulse-profile/README.md) verifies native resolution and job execution. Installed scheduling and release acceptance remain open.

The operator deployment must perform these actions:

1. Back up the selected profile, native user configuration, and release manifest.
2. Verify the selected LifeOS root and its current local owner grant.
3. Verify that the installed Hermes command supports all three owner jobs.
4. Install `PULSE.user.toml` into `LIFEOS/USER/CONFIG` within that selected root, with mode `0600`.
5. Configure the daily guest timezone as `America/Toronto`.
6. Leave excluded notification credentials unset.
7. Verify the current configuration and policy binding before starting Pulse.
8. Test actual job execution, restart, and the selected private model routes.
9. Add governed Discord delivery after the private channel passes acceptance.

Schedules use the guest's local timezone. The profile runs consolidation at 03:00, cleanup at 03:45, and the morning brief at 07:00. It retains the shipped cost aggregation and healthcheck schedules. It disables voice, GitHub Work, Cloudflare Synapse, and Claude quota reporting. The profile preserves the private FlashNext tier settings.

To reverse the configuration change, stop Pulse, restore the retained user configuration, verify its policy binding, and restart the verified previous release. Do not enable raw memory job commands while managed ownership is active.
