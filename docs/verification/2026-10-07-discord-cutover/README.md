# Permanent Discord gateway cutover

Date: 2026-10-07. Adrian selects `.252` as the sole future server and authorizes reuse of the existing Discord bot.

The [deployment snapshot](deployment.json) records the source shutdown, destination connection, tested revisions, and current limits. The source gateway is inactive and masked. Its active configuration no longer contains the bot token. Existing source backups remain. The destination user service is active and enabled with linger. It connects as Shiny Hermes Bot in the existing `#hermes-212` channel.

## Verified preparation

- The supported Hermes candidate applies all 11 compatibility patch groups.
- The supported LifeOS candidate applies all 23 compatibility patch groups.
- The destination runtime and Discord extra install successfully after `libatomic1` installation.
- Plugin validation passes. It reports the stock `pre_llm_call` declaration warning on the patched host.
- The fresh native installation and transactional mount complete for Adrian and Cerebo.
- The private FlashNext carrier probe reports `HOLDS` at xhigh effort. Tier settings retain their existing values.
- Credential files, configuration, capture configuration, and the recovery archive have mode 0600. The capture root has mode 0700.
- The recorder's initial inventory sees all 74 registrations. Its 29 startup events contain no reported losses, capture gaps, incomplete invocations, or integrity issues.
- Discord history access returns HTTP 200 from the destination account.

These preparation checks do not close `release-adapter-01`. Managed memory ownership is not configured. No source conversations, personal memory, or scheduled jobs are imported.

## Live acceptance

Adrian confirms availability for the live tests. The first request uses marker `D252-ANSWER` and asks the model to call `clarify` with choices `D252-A` and `D252-B`. Adrian selects the second choice. Subsequent requests must verify a genuine timeout and cancellation through Discord.

At this snapshot, no post-cutover test message has arrived. Question delivery, the answer, timeout, and cancellation remain pending. The acceptance timeout is temporarily 120 seconds. Restore 3600 seconds after the tests.

## Evidence and recovery

Private installation logs, receipts, identity originals, configuration archive, diagnostics, and Discord test messages stay under `/home/lifeos-hermes/migration/2026-10-07/` on `.252`. The recorder writes to `~/.local/state/lifeos-development-capture` as run `development-20261007T161339Z`. Captured conversation content stays outside Git.

Recovery stays on `.252`. Stop its gateway before restoring its private configuration archive, then restart and verify the connection. Do not reconnect the bot on `.212`.

The [cutover notes](../../../notes/2026-10-07-discord-cutover.md) retain the partial-clone trap and the measured native mount failure with indentless YAML lists. The prepared account uses conventional list indentation. Voice, managed memory activation, and combined release verification remain separate gates.
