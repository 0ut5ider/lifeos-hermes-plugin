# One private Discord channel controls

Date: 2026-10-07. Scope: the candidate daily text release. Adrian selects one private server text channel. The live bot still uses the accepted Step 1 runtime. These controls do not establish daily release readiness.

## Channel restriction

The Hermes lifecycle patch adds `DISCORD_GUILD_CHANNEL_ONLY`. Enabled mode requires one numeric allowed channel. It refuses direct messages, other server channels, threads, and slash commands outside that channel. The adapter destination resolver and standalone background sender enforce the same restriction. The default destination does not override an explicit forbidden destination.

Nine tests pass on the Discord SDK 2.7.1 installed on `.252`. The tests construct SDK messages, interactions, channels, and pairing records. They do not connect a bot or send a Discord message. The standalone positive control reaches credential validation for the selected channel. It does not test network delivery. The isolated token scope contains an empty synthetic credential.

The retained failing controls identify the missing admission, adapter destination, and standalone destination checks. The final [SDK output](standalone-after.txt) passes all nine tests.

## Memory audience

The candidate binds a private destination to a guild, owner, and bot. It reads the current bot identity, channel, guild, roles, and paginated members through Discord's API. It requires an explicit default-role denial and exactly the owner and bot as readers. Additional members or administrators prevent admission. Invalid responses, unavailable credentials, redirects, and changed bindings prevent admission.

The tests use an HTTP protocol fixture and real native memory operations. They cover permission precedence, pagination, malformed identifiers, identity changes, and revoked permission after an admitted read. A model call from a retained conversation also rechecks the audience. Native prompt admission refuses a changed audience.

The [focused gate](focused.txt) passes 77 tests and 151 subtests. After the final SDK patch changes, the [patch gate](patch-final.txt) passes nine tests and 107 subtests. The patch gate verifies source preparation, patch assignment, and bundled patch consistency.

The installed Hermes plugin scanner reports `safe` and permits installation. It reports seven low and 44 medium advisory findings across the candidate. It reports no findings for `discord_audience.py`. The [scanner summary](runtime-scan.json) retains those counts. The complete scan stays outside Git.

The read-only live Discord probe finds no explicit default-role denial on the current `#hermes-212`. It also confirms that the bot lacks permission to create channels. The operator must obtain the selected private channel ID and verify its actual permissions. No private destination grant is enabled by these tests.

## Fresh store and service admission

The authenticated dashboard on `.252` prepares and selects a fresh Adrian and Cerebo store with zero adopted facts. The selected review is `57f85fcebda64a5ab44838ecfa9c3c6a`. The selection journal reports `applied`. Original installations remain retained. Managed ownership and sharing remain disabled.

An actual selection creates a Pulse service drop-in with mode 0664 under the account's umask. Profile admission refuses it. The selection worker now publishes that file atomically with mode 0600. A filesystem regression reproduces the failure and verifies the corrected admission.

Operator changes on `.252` align the dashboard working directory and Pulse home with the selected store. A private `PULSE.user.toml` disables voice, iMessage, syslog, DA, and Bunker. These optional modules are outside the chosen release configuration. Gateway, dashboard, and Pulse run. Profile service admission passes. Background job memory and model acceptance remain open.

Operator changes remain outside Git. Their receipts are private files under the account's `migration/2026-10-07/daily-text/` directory. To return, use the recorded installation selection procedure while ownership remains disabled. Remove the added dashboard `daily-text.conf` and selected `PULSE.user.toml` only when that return procedure restores the earlier service home. Reload and restart the selected services. Do not restore the insecure Pulse file permissions.

## Evidence and remaining gates

The Step 1 ledger retains the exact historical patch rebuild script under [historical](historical/rebuild_hermes_patches.py). Its hash is unchanged. The ledger path changes because the active rebuild script now includes the channel test file. The historical evidence does not claim that this candidate passes the combined release gate.

The candidate is not deployed to the live gateway. Live channel acceptance, memory ownership setup, complete native writer coverage, background inference, backup recovery, and the combined release remain open. The final send path still needs an audience check for permission changes during generation. Channel ID enforcement alone does not close that gate.
