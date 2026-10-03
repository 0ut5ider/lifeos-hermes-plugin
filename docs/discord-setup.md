# Discord setup for a Hermes and LifeOS test installation

This guide records the steps that made the isolated `.212` Hermes installation work with Discord. Discord is a Hermes gateway connection; the LifeOS hook bridge does not own the bot token or create the gateway service. Use a separate bot for each simultaneously running Hermes gateway. Keep the bot token outside Git.

The [Hermes Discord guide](https://hermes-agent.nousresearch.com/docs/user-guide/messaging/discord) is the upstream reference. Check it when the Developer Portal or Hermes version changes.

## 1. Create and install the Discord bot

1. Create an application in the [Discord Developer Portal](https://discord.com/developers/applications). Choose the bot template or create a blank application. Set the bot's username on its **Bot** page.
2. On **Bot**, enable **Public Bot** if you will use Discord's provided install link. Leave **Requires OAuth2 Code Grant** off. Enable the **Message Content** and **Server Members** privileged gateway intents, then save. The message content intent was required to clear the connection error in our setup.
3. On **Bot**, reset and copy the bot token. Treat it as a password. The **Installation** link and application ID are not bot tokens.
4. On **Installation**, enable **Guild Install**. Choose **Discord Provided Link**. Under Guild Install, select the `bot` and `applications.commands` scopes. Select **View Channels**, **Send Messages**, **Embed Links**, **Attach Files**, and **Read Message History**. Select **Send Messages in Threads** and **Add Reactions** for the conversation behavior used here. Select **Create Public Threads** if you want Hermes to start a thread after a channel mention. Do not grant **Administrator** for this setup.
5. Open the provided install link, choose the test server, and authorize the bot. You need permission to manage that server.
6. In Discord, enable **User Settings → Advanced → Developer Mode**. Right-click your profile and copy your numeric User ID. Also copy the target channel ID if you want scheduled messages delivered there.

## 2. Prepare the Hermes account

Install the Discord dependency as the same Linux user that runs Hermes:

```sh
hermes pm install --extra discord
```

Configure the bot with `hermes gateway setup`, or set `DISCORD_BOT_TOKEN` and `DISCORD_ALLOWED_USERS` in that account's private `~/.hermes/.env`. The allowed-users value is your numeric Discord User ID. Set `DISCORD_HOME_CHANNEL` to a numeric channel ID if you want `discord` without an explicit channel ID to be the destination for proactive messages. Do not put credentials in the plugin repository.

Install a persistent user gateway service:

```sh
hermes gateway install --start-now --start-on-login
systemctl --user status hermes-gateway.service
```

The `.212` gateway had previously been started by the dashboard. After it stopped, the dashboard did not relaunch it, and its Start button reported that the service was missing. Installing the user service fixed that. On a server that must run the service after logout, enable systemd linger for the Hermes account if it is not already enabled. The `.212` account already had linger enabled.

## 3. Check network access

The bot needs outbound HTTPS and WebSocket access to Discord. The `.212` test account originally had a LAN-only nftables rule that blocked both the Discord dependency installation and the bot connection. An approved persistent rule now allows UID 1004 outbound TCP port 443 **to any internet destination** before the reject rules. This is a broad HTTPS exception, not a Discord-only allowlist. The rule lives in `/etc/lifeos-hermes-test-egress.nft`, loaded by `lifeos-hermes-test-egress.service`. The previous file is backed up at `/etc/lifeos-hermes-test-egress.nft.before-discord-20260928-082859`.

For a new restricted installation, decide its outbound network policy before connecting the bot. Test the ruleset with `nft --check` before applying it. A static Discord IP allowlist is brittle because service addresses can change. The plugin does not change the firewall. Do not copy the `.212` UID into another account's rules.

## 4. Verify both directions

Check gateway service status and the Hermes Channels page. Then send one outbound message to a test channel:

```sh
hermes send --to discord:<channel-id> "Hermes outbound test"
```

Confirm that the message appears as the intended test bot. This checks outbound Discord REST delivery. It does **not** prove that the gateway receives Discord events. In the channel, send `@Your Bot inbound test`. Hermes requires a mention in server channels by default. A plain channel message may be ignored correctly. The bot should reply, often in a thread it creates. Inside a thread where it has participated, the default behavior accepts follow-up messages without another mention. A direct message to the bot also needs no mention. Check `hermes sessions list --source discord` if the bot stays silent.

On `.212`, an outbound message appeared in `#general`. An unmentioned `READY-212` was ignored. A message mentioning Shiny Hermes Bot created a thread and received a `READY-212` response. This verified inbound gateway events and outbound replies with the separate test bot.

Discord can show the bot account and its same-named role as identical `@Shiny Hermes Bot` labels. The raw form `<@bot-user-id>` mentions the bot account. The form `<@&role-id>` mentions a role, and Hermes's channel mention rule ignores it. On `.212`, two 10:42 and 10:54 test requests used the role form and produced no Hermes session or watchdog. Select the bot account in Discord's member list, or send the request inside a thread that the bot already joined. Check the raw message through Discord's API if the visual label is ambiguous.

To make one channel mention-free, set `DISCORD_FREE_RESPONSE_CHANNELS` to its channel ID. Keep `DISCORD_REQUIRE_MENTION=true` for other channels. If you also want a thread for each top-level message in that free-response channel, set `DISCORD_FREE_RESPONSE_AUTO_THREAD=true`; the default is inline replies. Restart the gateway after configuration changes.

### Use a separate channel for each Hermes instance

Two bots in a shared free-response channel can both answer the same message. Give each gateway its own channel and preserve its user allowlist. Set these values in that gateway account's private `~/.hermes/.env`, replacing the channel ID:

```dotenv
DISCORD_ALLOWED_CHANNELS=123456789012345678
DISCORD_FREE_RESPONSE_CHANNELS=123456789012345678
DISCORD_REQUIRE_MENTION=true
DISCORD_FREE_RESPONSE_AUTO_THREAD=false
DISCORD_HOME_CHANNEL=123456789012345678
```

`DISCORD_ALLOWED_CHANNELS` restricts server-channel admission to the selected channel and its threads. `DISCORD_FREE_RESPONSE_CHANNELS` accepts ordinary messages there without an @ mention. `DISCORD_FREE_RESPONSE_AUTO_THREAD=false` keeps replies inline. `DISCORD_HOME_CHANNEL` sets the default destination for proactive delivery. Keep `DISCORD_ALLOWED_USERS` set to the intended user's numeric ID. Channel admission and direct-message admission are separate rules.

On 2026-09-30, `.212` moved to `#hermes-212`, channel `1554859357374513222`. The gateway accepted a plain message and delivered its reply. The `.213` configuration was not changed. Existing cron jobs with an explicit destination retain that destination; changing the home channel does not rewrite them.

Back up `.env` before changing these values. Restart the gateway after active turns finish, then verify a plain message in the selected channel. Restore the backup and restart the gateway to undo the routing change.

## 5. Verify scheduled delivery separately

Hermes cron can send output to `discord:<channel-id>`. For a disposable delivery test, run the following as the Hermes account, replacing the channel ID:

```sh
mkdir -p ~/.hermes/scripts
printf '%s\n' '#!/bin/sh' 'echo "Hermes scheduled delivery test"' > ~/.hermes/scripts/discord-delivery-test.sh
hermes cron create 1m --name discord-delivery-test --deliver discord:123456789012345678 --repeat 1 --script discord-delivery-test.sh --no-agent
hermes cron runs
```

After the job completes, confirm the marker in Discord and remove `~/.hermes/scripts/discord-delivery-test.sh`. On `.212`, the first attempt failed because a source-install cron worker used a Python environment without `ruamel`; [the worker bootstrap patch](../patches/hermes-cron-bootstrap.patch) made it use Hermes's managed dependency environment. Check `hermes cron runs` as well as the Discord channel when testing a new installation. A successful `hermes send` does not prove cron delivery works.

A scheduled channel post by itself does not create a daily conversation thread. Before promising a daily thread, configure and test the exact creation path, target channel, local time zone, and prompt. No recurring morning job was installed on `.212` during this test.
