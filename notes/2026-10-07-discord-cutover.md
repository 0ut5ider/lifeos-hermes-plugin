# 2026-10-07: Permanent Discord gateway cutover

Adrian confirms that `.212` will be decommissioned. `.252` is the sole future development server. Reuse the existing Discord bot and its channel configuration. Do not plan a fallback to `.212`. Preserve the fresh-store decision and do not transfer personal history.

The live source gateway runs as `lifeos-hermes`, UID 1004. The destination account is `lifeos-hermes`, UID 1008. Account IDs differ, so source firewall rules must not be copied unchanged. The source gateway remains active during destination preparation.

An attempted `git bundle create --all` from the test account's partial clone fetched historical promisor objects instead of producing a small transfer. The source `.git` was about 780 MB. We stopped that operation. A separate clone followed by checkout of the supported Hermes commit succeeded. The candidate preparation helper then applied all 11 Hermes patch groups. Runtime preparation now uses the supported installer stages, without sharing a temporary account's dependency environment.

The remaining Discord acceptance requires actual question delivery, an actual user answer, timeout behavior, and cancellation behavior. Synthetic callback tests do not satisfy this gate.

The destination installer fails its pinned Node check when `libatomic.so.1` is absent. Installing Ubuntu `libatomic1` resolves that check. Apt also updates its three compiler runtime dependencies. The retry completes, including the Discord extra.

The native mount does not preserve the indentation of an indentless `plugins.enabled` YAML list when it inserts the guard. A staged diagnostic reports `ParserError`, `expected <block end>, but found '-'`, at line 10. Serializing the prepared account configuration with mapping indentation 2, sequence indentation 4, and sequence offset 2 produces valid staged YAML and enables the guard. This cutover uses that conventional indentation. The native helper's handling of other valid YAML list styles remains a product issue to track separately.

The native transactional mount completes for Adrian and Cerebo. The private FlashNext carrier probe reports `HOLDS` at xhigh effort. The source gateway stops before the destination starts. The source unit is now masked, with MainPID 0, and the active source `.env` no longer contains the bot token. Existing source backups remain. The destination connects as Shiny Hermes Bot and runs an enabled user service with linger.

The current recorder source is installed into the destination's managed base Python site directory. Its configuration pins nine inspected source fingerprints. New capture starts at `development-20261007T161339Z`. Raw evidence and configuration recovery files remain private on `.252` under the service account. Adrian confirms availability for actual Discord interaction. Live answer, timeout, and cancellation outcomes still need observation.

Adrian confirms that the first cancellation attempt sends Shiny Hermes Bot's `/stop` while the question waits. The capture records 120.595 seconds and a timeout notice. The bot's suggestion that this demonstrates cancellation is incorrect. Recovery afterward proves recovery from timeout only.

The gateway interruption probe uses real gateway state and a real clarification waiter. After stop, the generation increments but the waiter remains blocked and its entry remains pending. The four-case regression passes two characterization cases and fails both cancellation cases before the correction. Synchronous queue cleanup after generation invalidation makes all four pass. Another chat's entry remains live and late answers cannot resolve the cancelled entry.

Existing logs contain no slash invocation from the live attempt. That absence does not establish whether Discord delivered it. The external observer adds safe interaction and slash dispatch stages for the repeat. The screenshot shows two bots with `/stop`; Adrian identifies Shiny Hermes Bot. The waiter correction is confirmed independently. The live dispatch cause remains unresolved until the repeat.

The second cancellation attempt shows Discord's `Unknown Integration` error. No slash interaction reaches the observer, and the question times out after 120.312 seconds. Ctrl+R restores `/status` receipt, authorization, defer, and reply delivery. The startup sync compares explicit returned installation settings against an unset desired value, then deletes and recreates the command. That path changes `/stop`'s ID. A stale client command is the supported inference for the delivery failure.

The third cancellation attempt passes. The capture observes `/stop`, authorizes it, and invalidates generation 3. The question finishes after 17.954 seconds against a 120-second deadline. Both native question hooks exit 0. The bot sends its stopped notice, then returns `D252-RECOVERY-3-PASS` on the next request. Clearing the waiter produces the tool's empty timeout result, so the recovery model's timeout explanation is misleading. Timing and interruption establish cancellation.

The command identity regression first passes one characterization case and fails four cases. Inheriting the existing default contexts and using same-name/type upsert makes all five pass. An actual Discord upsert preserves `/stop` ID `1557471123728240801` and its version. The neighboring limit test stubs normalization and fails with a missing `contexts` key. It now uses the actual normalizer. Deployment and restart identity verification follow as one package.
