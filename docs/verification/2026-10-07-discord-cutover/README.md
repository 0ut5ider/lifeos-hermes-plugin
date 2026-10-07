# Permanent Discord gateway cutover

Date: 2026-10-07. The actual Discord answer, timeout, cancellation, and recovery tests pass on `.252`. These results close `release-adapter-01` in the approved Step 1 checklist.

Adrian selects `.252` as the sole future server and authorizes reuse of Shiny Hermes Bot. The bot uses the existing `#hermes-212` channel. The `.212` gateway is masked and inactive, with MainPID 0. Its active configuration no longer contains the bot token. Existing source backups remain.

The [initial deployment snapshot](deployment.json) records preparation and the first gateway start. The [latest deployment](command-identity/deployment.json) publishes code commit `2d07208`, restores the 3600-second question timeout, and verifies the running service. Its source manifest contains all 11 Hermes patch groups. The LifeOS candidate contains all 23 compatibility patch groups. The fresh native store uses Adrian and Cerebo. No source conversations, personal memory, or scheduled jobs are imported. The private FlashNext effort mapping stays unchanged.

## Live acceptance

The [answer evidence](answer.json) records the question at 16:37:36 UTC and the returned `D252-A` selection at 16:37:57 UTC. Adrian confirms that he clicks that choice. The bot reports the same choice. Both native question hooks exit 0.

The [timeout evidence](timeout.json) records an unanswered question at 17:19:50 UTC. The tool waits 120.38 seconds and returns an empty answer with a two-minute timeout notice. No answer arrives before the delivered report. Both native question hooks exit 0.

The [cancellation evidence](cancellation.json) records `D252-CANCEL-3` after a Discord client refresh. The question appears at 19:32:03 UTC. The observer receives Shiny Hermes Bot's `/stop` at 19:32:20 UTC. Authorization and defer succeed. The gateway invalidates the turn generation and releases the question. The tool finishes after 17.954 seconds against a 120-second deadline. Both native question hooks exit 0. The bot sends its stopped notice. The next request receives `D252-RECOVERY-3-PASS` at 19:33:09 UTC. Adrian confirms immediate stop and recovery and supplies a screenshot.

The clarification tool represents a cleared waiter as an empty timeout result. The recovery model therefore gives a misleading timeout explanation. The interruption events, measured duration, and next reply establish cancellation. The recorder redacts the `timed_out` boolean, so that field is not evidence for this result.

## Corrections and failed attempts

The [first cancellation attempt](cancellation-attempt.json) reaches the full timeout and does not verify cancellation. The [gateway regression](cancellation-regression/README.md) independently reproduces a waiter that remains blocked after interruption. Synchronous cleanup after generation invalidation releases the waiter, rejects late answers, preserves another chat's question, and permits a successor question.

The [second attempt and refresh](slash-refresh.json) show `Unknown Integration` before gateway delivery. Ctrl+R restores actual `/status` receipt and reply delivery. The [command identity regression](command-identity/README.md) verifies that the startup comparison deletes and recreates unchanged commands when Discord returns explicit default installation settings. A stale client command remains the supported inference for that delivery failure.

The command sync correction compares inherited settings without treating them as edits. Changed commands use Discord's same-name/type upsert route. The real API preserves `/stop` ID and version. After deployment, startup preserves all 69 existing command IDs and versions and creates the missing `kanban` command. It updates, deletes, and recreates no existing commands. Nine deployed regression cases, 14 neighboring Discord cases, and 13 patch and source transaction cases pass.

## Evidence and recovery

The final capture snapshot contains 2,679 events with no incomplete invocations, losses, capture failure processes, capture gaps, or integrity issues. The recorder pins 10 inspected sources. Its registration identities include observed configuration versions; the installed native inventory remains 74 registrations.

Private receipts, diagnostics, configuration recovery files, and raw Discord messages stay under `/home/lifeos-hermes/migration/2026-10-07/` on `.252`. The recorder writes under `~/.local/state/lifeos-development-capture` as run `development-20261007T161339Z`. Conversation content and screenshots stay outside Git. The capture root has mode 0700. Credential and configuration files have mode 0600.

The latest deployment record names the private rollback directory. Stop the gateway before restoring saved source files, the source manifest, the plugin package, profile configuration, and capture configuration. Restart the gateway and verify its connection. The rollback configuration contains the temporary 120-second timeout. Set 3600 seconds when acceptance testing is finished. Do not reconnect the bot on `.212`.

The [cutover notes](../../../notes/2026-10-07-discord-cutover.md) retain the partial-clone trap and native mount failure with indentless YAML lists. Runtime installation needs Ubuntu `libatomic1`. Plugin validation passes with the documented stock `pre_llm_call` declaration warning. Managed memory activation, Discord voice, and broader combined release verification remain separate gates.
