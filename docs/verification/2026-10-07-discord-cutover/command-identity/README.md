# Discord command identity regression

Date: 2026-10-07. A gateway restart changes the existing `/stop` command ID. The Discord client reports `Unknown Integration`. Refreshing the client restores `/status` delivery.

The [comparison probe](before-comparison.json) uses actual Discord command models and the registered Hermes command tree. The server returns explicit installation settings. The desired command leaves those settings unset. Hermes treats that difference as a change and deletes the existing command before creating its replacement.

The [before output](before.txt) records one passing characterization case and four failing cases. The [after output](after.txt) records five passing cases. The tests use real Discord models and command trees with isolated transport state. They do not establish live Discord acceptance.

The correction compares unset installation and interaction contexts against the existing command settings. An unchanged command requires no write. A changed command uses the same-name/type upsert route. The route accepts all command fields without deleting the existing command.

The [live API check](live-upsert.json) submits the existing `/stop` fields to Discord. Discord returns HTTP 200 and preserves both ID and version. This result verifies the identity behavior of the real API. Discord documents this route in its [application command reference](https://docs.discord.com/developers/interactions/application-commands#create-global-application-command).

The [neighbor checks](neighbors.txt) cover connection behavior and deletion before creation at the command limit. The limit test replaces the normalizer with a mock that omits required fields. That fixture first fails with `KeyError: 'contexts'`. The fixture now uses the actual normalizer.

The dependency model converts the raw `[0, 1]` installation settings to `[0]` on this pinned runtime. The comparison proof therefore reports model output. The correction does not change the dependency. Explicit user-install settings require separate dependency verification.

The [live cancellation evidence](../cancellation.json) verifies `/stop` and the next message before this command sync correction deploys. The subsequent deployment separately verifies command identity after restart.

The [deployment record](deployment.json) publishes commit `2d07208` at 19:42 UTC and restores the 3600-second question timeout. Shiny Hermes Bot reconnects. Startup preserves all 69 existing IDs and versions. It creates the missing `kanban` command, with no updates, deletions, or recreations. All [nine deployed regression cases](deployed-tests.txt) pass. The recorder pins 10 sources and reports no capture gaps, losses, or integrity issues in its 2,679-event snapshot. The `.212` gateway remains masked and inactive.

Rollback stays on `.252` in the directory named by the deployment record. Stop the gateway before restoring its saved source files, source manifest, plugin package, profile configuration, and capture configuration. Restart the gateway and verify its connection. The saved configuration restores the temporary 120-second timeout, so set 3600 seconds when the acceptance test is no longer needed.
