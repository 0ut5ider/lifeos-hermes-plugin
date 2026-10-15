# Bind selected commands and the service inventory

Date: 2026-10-15.

The independent removal workflow review finds two adjacent gaps. A changed stock launcher passes the source and manifest checks, then the selected command exits with status 91. An actual inactive runtime-linked user service also passes admission while it names the Bun and native programs selected for removal. The primary reproduces both failures.

The stock review now binds the three commands, Python environment, contained tool store, package-manager bootstrap, enabled features, and runtime metadata. The source binding stays separate. Every dependency link must resolve inside the fixed stock runtime. The executable check excludes bytecode caches and the Python environment's non-executable `.lock` file. The real constructed environment has exactly one shared-write artifact: that lock file, with mode 0666. All executable files still require owner control without shared write access.

The real 2.2 GiB stock runtime passes the seven-component binding check in 4.093 seconds. The synthetic mutation controls cover all three commands, interpreter bytes, dependency bytes, bootstrap bytes, and enabled features. A later interpreter link outside the runtime refuses admission.

Consumer admission now reads the account manager's effective unit paths and loaded fragment, override, and execution metadata. It scans inactive runtime-linked units and preserves their definitions. The primary also finds stale loaded fixture fragments whose temporary directories no longer exist. Admission checks their cached execution metadata and does not treat an unrelated missing file as a selected program. The actual linked-service regression and the existing consumer tests pass.

The broader 144-test run passes after moving an earlier crash hook to its intended boundary: the queue is published, but owner admission has not started. The original failure remains in the evidence. These results do not certify the pending full installed removal or a model turn.

The next review disproves the bytecode exclusion assumption. A valid timestamp cache executes different code while source bytes stay unchanged. The primary reproduces that behavior with actual Python. The executable closure now includes bytecode and source caches. Stock commands, the detached worker, the constructor probe, and the standalone helper select a contained cache prefix and disable cache writes. A real child ignores an adjacent injected cache, reads the reviewed source, and creates no cache directory. The original excluded-cache test now requires refusal.

The review also runs an actual inactive oneshot service through `/usr/bin/env bun` with the private executable on PATH. The literal path scan misses this dependency. Consumer admission now refuses basename Bun references in foreign definitions and loaded execution metadata. The exact two probes and the related controls pass 46 tests. These changes remain unreleased.

The next adjacent probe selects an interpreter link inside the runtime but outside the hashed components. Its changed target executes with status 94 while the admitted identity stays unchanged. The native builder is not shown to emit this layout. The fix refuses such a link before plan creation, including links into the excluded source profile or environment lock. A directory-link control covers the same boundary. All 1,068 links in the actual stock fixture target covered components. The original mutation probe now stops at its baseline preparation; that result is recorded as an early refusal, not as a passing unmodified probe.
