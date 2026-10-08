# Current audience before Discord delivery

Date: 2026-10-08. Scope: the daily text release candidate. The live gateway does not run this candidate.

The [initial SDK experiment](before.txt) posts generated text and edits a message after another member gains channel access. Five controls fail, and one control observes the absent callback. The unchanged-audience control sends an actual authenticated HTTP request.

The selected private-channel mode now requires `pre_message_delivery`. The host compares the transport credential with the current profile credential. The callback receives platform, channel, guild, and profile identifiers. It receives no content or credential. LifeOS reads current channel permissions and verifies the configured owner and bot. It also checks configuration again after the permission reads. A missing, unknown, failed, timed-out, or late policy result cannot admit a write.

The guard precedes each reply chunk, reply-reference retry, streaming edit, final edit chunk, interactive prompt, card edit, attachment, and standalone post. A permission refusal during an oversized final edit reports failure with its partial delivery count. It preserves existing transport failure reporting. Question and picker timeout controls preserve normal card updates while withholding updates after an audience change.

The [combined result](gate-results.json) passes all four groups, 168 tests in total:

- [47 package controls](package-final.txt), including 21 actual SDK and HTTP delivery controls, native memory admission, plugin registration, and provider checks.
- [9 SDK channel controls](sdk-channel-final.txt) through actual Discord objects.
- [83 native unit controls](native-final.txt), including required policy dispatch, timeout suppression, media receipts, views, and simulated transport behavior.
- [29 installation controls](install-final.txt), including capability declarations, process interruption, source admission, and complete patch regeneration.

The selected runtime uses Discord SDK 2.7.1, aiohttp 3.14.3, and pytest 9.1.1. The [runner](run_gate.py) records a durable completion marker. The [complete source preparation](source-preparation-final.txt) applies all eleven Hermes and twenty-three LifeOS patch groups. Both distributed patch copies match.

Earlier diagnostic runs remain recorded. One test expects a marker outside its actual first chunk. Another expects no policy registration before installation, but the required guard must refuse delivery when configuration is missing. The initial capability check identifies the undeclared hook; the manifest now declares it. Installation checks also select an older rebuild source and inherit ignored `SIGINT` from the detached shell. The [signal probe](detached-signal-probe.json) verifies that disposition. The final runner selects the prepared source and restores normal interruption handling before launching children.

The upstream gateway pytest fixture substitutes Discord objects before test imports. Its simulated unit tests require those objects. Preloading the real SDK into those simulated fixtures causes incompatible constructors and unclosed fixture files. The final gate runs the intended unit fixture environment separately from actual SDK and HTTP checks. It does not skip the failing selections or count them as passing evidence.

The Step 1 ledger retains the historical registration code under [plugin-registration.py](../2026-10-07-private-channel/historical/plugin-registration.py). Its original hash stays unchanged. The [historical ledger check](historical-ledger-final.txt) passes. This preserves prior evidence; it does not establish combined acceptance for this candidate.

These controls use a local HTTP protocol fixture. Live private-channel acceptance still requires Adrian's channel ID and actual Discord permissions. Reading permissions before delivery does not make the read atomic with Discord's write. It cannot remove content already posted before permissions change. Memory writer completion, installed ownership, scheduled jobs, actual backup recovery, and combined release acceptance remain open.
