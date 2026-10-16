# Discord text setup

This guide describes the qualified LifeOS mode: one private server text channel, one owner, and one bot for that Hermes instance. The restricted mode refuses direct messages and threads. Discord voice input and spoken replies remain [deferred](../TODO.md).

Start with the [complete integration](installation-workflow.md) and a working Hermes model. Keep development and daily bots separate so that a development gateway cannot answer daily messages or consume its bot connection.

## Create and install the bot

1. Create an application in the [Discord Developer Portal](https://discord.com/developers/applications).
2. Configure its bot and enable the **Message Content** and **Server Members** privileged intents.
3. Leave the OAuth2 code-grant requirement off for the tested bot installation flow.
4. Configure guild installation with the `bot` and `applications.commands` scopes.
5. Request **View Channels**, **Send Messages**, **Embed Links**, **Attach Files**, **Read Message History**, and **Add Reactions**.
6. Install the bot into the intended Discord server.
7. Generate the bot token and enter it only through the intended account's private Hermes configuration.

The restricted text profile does not require thread, voice, or Administrator permissions. A bot token is a credential; an application ID or installation link is not the token. Keep it out of chat, Git, screenshots, and verification receipts.

Enable Discord Developer Mode to copy the numeric owner, guild, bot, and channel IDs. Create one private text channel. Deny **View Channel** to `@everyone`, and allow only the owner and selected bot to read it.

Discord server owners and administrators bypass channel permission overwrites. The memory audience check inspects current roles and members and refuses additional readers. The Server Members intent is needed for that verification.

## Configure the Hermes account

Use `hermes gateway setup` as the same account that runs Hermes. The token and audience settings belong in that account's selected private profile, not the plugin repository. If the installed runtime lacks the Discord dependency, the Hermes package command is `hermes pm install --extra discord`; retain the qualified environment and verify its identity afterward.

Configure the restricted mode with actual numeric IDs:

```dotenv
DISCORD_ALLOWED_USERS=<owner-user-id>
DISCORD_ALLOWED_CHANNELS=<private-text-channel-id>
DISCORD_GUILD_CHANNEL_ONLY=true
DISCORD_FREE_RESPONSE_CHANNELS=<private-text-channel-id>
DISCORD_NO_THREAD_CHANNELS=<private-text-channel-id>
DISCORD_AUTO_THREAD=false
DISCORD_FREE_RESPONSE_AUTO_THREAD=false
DISCORD_HOME_CHANNEL=<private-text-channel-id>
```

`DISCORD_GUILD_CHANNEL_ONLY=true` requires exactly one numeric allowed channel. The integration gates incoming messages, slash commands, adapter sends, and standalone sends. The free-response setting permits ordinary messages there without a mention. Replies stay inline.

Channel allowlisting is separate from lasting-memory authority. The owner must also bind the guild, owner, bot, private destination, and selected model route through the governed memory setup. A private-looking channel or successful message alone does not grant memory access.

Retain a private configuration backup before editing. Restart the gateway after active turns finish, then verify the current settings. Restore that backup and restart to undo a routing change.

## Start and check the gateway

A managed first installation leaves newly created gateway and Pulse services disabled until setup and authority are accepted. Check the actual user service and the Hermes Channels page before starting daily use.

```bash
systemctl --user status hermes-gateway.service
```

If a standalone Hermes account needs a persistent service, its native command is:

```bash
hermes gateway install --start-now --start-on-login
```

For an already managed installation, inspect the existing service before recreating it. The release manager verifies those definitions. A server that must run the account's services after logout also needs systemd linger, configured by its administrator.

The bot needs outbound HTTPS and WebSocket access to Discord. Check the server's actual network policy. The integration does not install firewall rules. Do not copy another host's account IDs or firewall exceptions.

## Verify conversation and memory separately

1. Send a plain test message in the selected private channel.
2. Confirm that the intended bot replies inline.
3. Run `/status` from that bot and confirm that it responds.
4. Confirm that another channel, a thread, and a direct message are refused by the selected restriction.
5. Complete owner memory activation and start a fresh conversation.
6. Save a synthetic project fact through the governed tool, start another session, and recall it through the governed search tool.
7. Forget that synthetic fact through governed memory and verify that ordinary recall excludes it.

A successful outbound send does not establish inbound gateway delivery. A chat reply does not establish lasting-memory save and recall. Use the actual tool status and reference for the memory check.

If Discord shows duplicate slash commands from different bots, select the intended bot's entry. Refresh Discord when stale integration data prevents delivery. The [live cancellation acceptance](verification/2026-10-07-discord-cutover/README.md) records the earlier command-identity and interruption checks.

## Verify scheduled delivery separately

Existing scheduled jobs with an explicit destination keep that destination when the home channel changes. Review the scheduler definition, timezone, admission, model route, and exact channel before enabling a recurring message.

The [daily profile contract](deployment/daily-text/README.md) describes the governed morning delivery command and backup coverage for the project's selected deployment. It is an operator-specific package input, not a configuration to copy unchanged to another owner.

A scheduled acceptance must observe the actual automatic execution and complete delivery window. Do not run a job manually or send a substitute message to manufacture that evidence. The [verification index](verification/README.md) distinguishes the original morning and owner-rescheduled evening observations.

## Other Hermes modes and historical fixtures

General Hermes can support mentioned server messages, threads, and direct messages. Those modes are separate from this qualified private-channel profile and need their own audience and memory acceptance. Do not enable their thread or DM behavior inside the restricted configuration above.

The [historical Discord snapshot](history/2026-10-16-discord-setup.md) retains the earlier `.212` to `.252` migration, local bot IDs, firewall observations, generic Hermes modes, and disposable cron test. The [daily acceptance record](verification/2026-10-11-daily-guest/README.md) retains the separate daily bot and cross-session memory checks.
