# Restore review closure

Date: 2026-10-02

Broad regression implementation under test: `1333713`. Admission correction: `befae76`. Recovery scheduling correction: `2ef78f3`.

The [first Sol review](../../agents/2026-10-02-sol-review-fixes/sol-review-fixes.md) reproduced three remaining restore defects. The primary independently reproduced those defects before changing the implementation. See the review's `primary-validation/` directory for the failing regressions and subsequent results.

## Corrections

1. Replaced profile files and the baseline move into private directories beside their original targets. The moves stay on each target filesystem.
2. Each update snapshot records the retained paths before its archive moves. Interrupted restoration keeps those files available for inspection and recovery.
3. Restore checks profile contents before the program swap. Later writes move into the retained archive.
4. Worker exceptions report unfinished swaps as `interrupted`. The authenticated dashboard can issue fresh recovery authority. Harmless restore refusals retain `applied` status.
5. The recovery route refuses other origins, query parameters, and request bodies before changing the job or issuing a grant.
6. The route awaits the request guard, then runs status inspection, authorization, and launch in the existing thread pool. Service checks do not block other dashboard requests.

## Verification

The regression runner uses disposable local files, local HTTP routes, and pinned prepared native sources. The source commit is saved in `source-commit.txt`. `run-gate.sh` saves Python, recorder, and dashboard results with their exit codes.

The real two-filesystem test uses `/tmp` and `/dev/shm`. It covers restore, failed update rollback, and recovery after interrupted baseline publication. A process-kill regression checks retained configuration after its archive rename and before replacement. The administrative route case executes the worker error handler and authenticated recovery admission. It replaces worker execution and service launch, so it is a component test.

The independent closure review writes its report and probes to [the Sol closure review directory](../../agents/2026-10-02-sol-restore-closure-review/).

The broad gate passes 354 Python cases, 32 development recorder cases, and 11 dashboard cases. It completes before the final recovery admission correction. The second reviewer closes R1 through R3 and reproduces an inherited request-admission gap in recovery. The primary independently confirms that other-origin, query, and body requests reached the launcher. The added regression fails in four assertions before correction. After correction, all 24 administrative dashboard cases pass. The same direct probes return HTTP 403, 400, and 400, create no grant, leave the job unchanged, and never reach the launcher.

The [admission review](../../agents/2026-10-02-sol-recovery-admission-review/sol-recovery-admission-review.md) confirms the request guard and current owner authorization. It reproduces an event-loop scheduling regression from the asynchronous endpoint change. A local launch subprocess waits 0.8 seconds. A concurrent request completes in 1.9 milliseconds on the parent commit, but waits 817 milliseconds on the guard commit. The primary independently reproduces that difference and adds an event-driven scheduling regression. The regression fails before correction.

After moving the synchronous sequence into the thread pool, all 25 administrative dashboard cases pass without warnings, skips, failures, or errors. The primary replays all 32 real loopback HTTP scenarios. Rejected requests preserve state, and valid requests receive action-bound recovery grants. The corrected scheduling probe serves another request in 5 milliseconds during an 818-millisecond captured launch. These measurements describe the local test, not production service timing. The [scheduling closure review](../../agents/2026-10-02-sol-recovery-scheduling-review/) records the independent final checks.

The final GPT-6.1-Sol review at high effort finds no material issue in that correction and its immediate caller contract. It independently passes 25 dashboard cases and 32 HTTP scenarios. Its scheduling comparison serves the concurrent request in 1.8 milliseconds during an 816-millisecond launch wait. The primary reruns the 25-case suite after the review and confirms clean results. The final implementation remains `2ef78f3`; subsequent commits contain evidence and documentation.

## Limits

These results do not establish live systemd update acceptance, actual browser clicks, power-loss durability, complete hook parity, or full memory activation. Same-account filesystem substitution and concurrent worker launch remain outside this correction's acceptance claim. Update archives retain profile data, including environment files. They remain private and intentionally retained. Temporary mount preparation copies follow the separate cleanup policy.

No server is changed or deployed. Memory ownership remains disabled on running installations. The PR remains in draft.
