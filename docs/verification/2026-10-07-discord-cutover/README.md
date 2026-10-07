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

Adrian confirms availability for the live tests. The first request uses marker `D252-ANSWER` and asks the model to call `clarify` with choices `D252-A` and `D252-B`. The actual tool result returns `D252-A`, and the delivered reply reports `D252-A`. Adrian confirms that he clicks `D252-A`. The returned option matches his selection. Question delivery and answer return pass. Subsequent requests must verify a genuine timeout and cancellation through Discord.

The [answer evidence](answer.json) records actual question delivery and answer return. The request arrives at 16:37:21 UTC. The bot posts the question at 16:37:36 UTC. The recorded tool result returns `D252-A` at 16:37:57 UTC. The bot delivers its matching report at 16:38:01 UTC. Both native question hooks complete with exit code 0. The capture contains 487 events with no reported losses, capture gaps, incomplete invocations, or integrity issues at this snapshot. Its 120 registration identities represent observed configuration versions, not 120 installed hooks.

The [timeout evidence](timeout.json) verifies the unanswered `D252-TIMEOUT` request. The bot posts the question at 17:19:50 UTC. The tool waits 120.38 seconds and returns an empty answer with the notice `[user did not respond within 2m]`. No user text arrives between the request and the delivered timeout report at 17:21:56 UTC. Both native question hooks complete with exit code 0. The capture's 873 events contain no reported losses, capture gaps, incomplete invocations, or integrity issues. The recorder redacts the `timed_out` boolean; the empty answer, notice, duration, and delivered report remain observable.

Cancellation and post-cancellation recovery remain pending. The acceptance timeout is temporarily 120 seconds. Restore 3600 seconds after the tests. The cancellation request uses marker `D252-CANCEL`. The intended sequence sends `/stop` while the question is pending, then sends `D252-RECOVERY` to verify that the session accepts a normal next turn.

The [first cancellation attempt](cancellation-attempt.json) does not verify cancellation. The bot posts the question at 17:45:20 UTC. The tool waits 120.60 seconds and returns another timeout at 17:47:22 UTC. The bot reports that timeout at 17:47:27 UTC. Its claim that this behaves as planned cancellation is incorrect. The normal recovery request arrives at 18:23:54 UTC and receives `D252-RECOVERY-PASS` at 18:24:08 UTC. Adrian supplies a screenshot of that reply. This verifies recovery after timeout. It does not prove that `/stop` interrupts a pending question. Confirm the action Adrian attempts before repeating cancellation. Keep `release-adapter-01` unverified.

## Evidence and recovery

Private installation logs, receipts, identity originals, configuration archive, diagnostics, and Discord test messages stay under `/home/lifeos-hermes/migration/2026-10-07/` on `.252`. The recorder writes to `~/.local/state/lifeos-development-capture` as run `development-20261007T161339Z`. Captured conversation content stays outside Git.

Recovery stays on `.252`. Stop its gateway before restoring its private configuration archive, then restart and verify the connection. Do not reconnect the bot on `.212`.

The [cutover notes](../../../notes/2026-10-07-discord-cutover.md) retain the partial-clone trap and the measured native mount failure with indentless YAML lists. The prepared account uses conventional list indentation. Voice, managed memory activation, and combined release verification remain separate gates.
