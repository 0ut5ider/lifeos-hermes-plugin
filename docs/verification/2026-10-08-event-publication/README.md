# Shared native event publication

Date: 2026-10-08. The release remains staged. These checks use synthetic event content and actual native processes.

The [baseline](baseline.txt) reproduces raw publication by unbound and read-only callers and publication to an alternate destination. It also shows that the original event uses the ambient session identifier. The baseline contains two setup failures: the new append operation and interruption helper do not exist yet. Those failures do not establish a product defect and do not count as passing checks.

The managed shared event library delegates appends to the owner service. The service requires unrestricted owner recall and publication authority, the fixed installed destination, bounded event fields, and current retirement policy. It sets the UTC timestamp and authenticated session identifier. The owner transaction journals and serializes each append. The native library retains its silent best-effort failure behavior. A standalone installation preserves native event overrides.

The [final focused gate](final-gate.txt) passes 12 tests. It compares original event fields, checks refusal without authority, rejects an alternate or symlink destination, excludes forgotten source text, prevents forged session attribution, verifies retries and actual concurrent emitters, and recovers the original history after an interrupted append. A separate native emitter starts during an actual finding publication. It waits for the owner transaction and then appends; the final history contains both events.

The [adjacent gate](adjacent-gate.txt) passes 69 tests without skips. It includes Knowledge conformance, lint, response authority, source labels, and publication recovery. The [source receipt](source-identity.json) records product and native emitter hashes. Both patch copies have identical bytes.

The current event history limit is 8 MiB. The service refuses larger publication rather than deleting history. This gate covers shared `appendEvent` and `emitFindingSet` writers, including MemoryDirIntegrity. It does not cover unrelated observability logs, arbitrary raw file appends, or all caller read boundaries. Installed application acceptance and complete native caller coverage remain open.
