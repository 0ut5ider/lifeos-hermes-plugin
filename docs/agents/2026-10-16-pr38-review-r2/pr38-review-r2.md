# PR38 review, round 2

- Date: 2026-10-16
- Role: independent reviewer (Claude Code, single agent, no delegates)
- Model: Claude Opus 5.5 (`claude-opus-5-5`)
- Question: Does the incremental change since round 1 (report commit `1476f532` and test-only repair `70fa8390`) keep a meaningful cancellation assertion and cleanup, are the incremental report claims accurate, and does any round 1 objection remain open?
- Range: base `455154c1`, previous reviewed head `99e18c44`, current head `70fa8390`.

## Verdict

**CLEAR.** I found no actionable defect in the incremental change. Round 1 had no open objection, and nothing in this increment reopens one.

## What changed

`git diff 99e18c44 70fa8390 --stat` shows 11 files. Ten are documentation and evidence (the round 1 report bundle, the qualification repair report, and the process exit note). The only code change is in `tests/test_memory_owner_job_processes.py`. `lifeos_hook_bridge/memory_owner_jobs.py` does not change in this increment. Across the full PR it changes by one line, an unused import removal. `_terminate` and `_command` are byte-identical to the base.

## Assessment of the test repair

`_terminate` (`lifeos_hook_bridge/memory_owner_jobs.py:40`) sends SIGKILL to the process group with `os.killpg`, then calls `process.wait()` on the direct child only. The kernel queues SIGKILL to every group member during the `killpg` call, but each member exits when it is next scheduled. `wait()` on the leader therefore does not order the grandchild's exit. The old assertion read the grandchild state immediately, so it raced that exit. The repair diagnosis is correct, and the product makes no stronger guarantee that a test should enforce.

The new `assert_stopped` (`tests/test_memory_owner_job_processes.py:29`):

1. It still requires the PID file to exist.
2. It accepts only an absent process (`FileNotFoundError` on open, `ProcessLookupError` on a read after the process is reaped) or the `Z` state.
3. It polls every 10 ms against one shared 5 second deadline for all PIDs, so the total wait is bounded.
4. It fails with the observed state when a process is still alive at the deadline.

This is still a meaningful cancellation assertion. A grandchild that escapes the kill (a parent-only kill, a new session, or a lost group signal) still sleeps for 60 seconds, so the assertion fails after 5 seconds. The assertion now accepts one extra case: a group kill that is late by up to 5 seconds. That is not a realistic defect class for `_terminate`. The observed lag is at most 4.18 ms.

The regression test `test_stop_assertion_waits_for_actual_process_exit` (line 45) gives the helper a direct child that runs for 0.5 seconds. That child becomes a zombie because the test does not reap it until `finally`. The old helper fails at once; the new helper waits and passes. The `finally` block kills and reaps the child on every path, so the test leaks no process.

## Verification of claims

| Claim | Check | Result |
|---|---|---|
| First archive run: 1,128 tests, 1,123 pass, 3 errors, 2 failures | `archive-integration-99e18c44.stderr` lines 1135 to 1231 | Confirmed: `Ran 1128 tests`, `FAILED (failures=2, errors=3)` |
| Two health errors are disk quota errors | Same stderr, lines 1135 and 1161 | Confirmed: `OSError: [Errno 122] Disk quota exceeded` in both health tests |
| One error and one failure are the known `/proc` account boundary cases | Lines 1187 (`PermissionError ... /proc/814420/exe`) and 1220 (`The account process boundary cannot be verified`) | Confirmed. These are the same two cases that round 1 records as a baseline. |
| One racy grandchild assertion failure | Line 1206, `Child 3840685 still runs` from the old assertion | Confirmed |
| 100-round probe: 12 nonterminal at return, all terminal within 4.18 ms | Recomputed from `termination-timing.json` | Confirmed: 12 rounds start in `R`, 24 in `Z`, 64 absent. All 100 end terminal. Maximum elapsed time is 4.175 ms for all rounds and 2.022 ms for the 12 nonterminal rounds. |
| All 16 health and process cases pass on replay | `unexpected-replay-r2.txt` | Confirmed: all 14 health tests (the module has 14 `def test_`) plus the 2 process tests that existed then |
| Initial replay misses a fixture variable | `unexpected-replay-r1.txt` | Confirmed: `KeyError: 'LIFEOS_HARVEST_CONTROL_SOURCE'` |
| Eight `/proc` boundary cases pass under a disposable service account | `docs/agents/2026-10-16-codebase-cleanup/codebase-cleanup.md:51` | A record exists. I did not rerun it. Round 1 also relies on this record. |
| The new regression fails on the old assertion | My replay (see Tests) | Confirmed |
| The parent-only kill mutation is detected and cleaned up | My replay (see Tests) | Confirmed |
| No product cancellation code change | `git diff 455154c1 70fa8390 -- lifeos_hook_bridge/memory_owner_jobs.py` | Confirmed: only the unused `NativeMemory` import is removed |

The repair report attributes the disk quota errors to concurrent reviewer exports on the workstation temporary filesystem. That cause is plausible, but the evidence does not prove it. The running archive with a private `TMPDIR` on the cache filesystem is the real check. Qualification correctly depends on that run.

## Tests I ran

Interpreter: `/home/outsider/.cache/lifeos-daily-promotion-20261014/frozen-test-environment/bin/python` (Python 3.14.7), with `-W error::ResourceWarning`, `PYTHONPATH=<repo>:<repo>/tests`, and `TMPDIR=~/.cache/pr38-r2/tmp`.

1. I ran each of the three real-process tests on its own. All three pass: stop assertion in 0.520 s, deadline in 1.005 s, termination in 0.196 s.
2. I ran the full process module 30 times in sequence. All 30 runs pass.
3. Red replay: I put the parent commit's `assert_stopped` body together with the new regression test in a scratch copy. The regression test fails in 0.002 s with `Child <pid> still runs`. This matches `process-assertion-red.txt`.
4. Mutation replay: I ran the repair's `mutate_termination.py`, which replaces `_terminate` with a parent-only kill. The deadline test fails after 6.012 s with `Child 4124412 still runs in state S`, and the script prints its PASS line. After the run, PID 4124412 is gone and no `time.sleep(60)` process remains.
5. The new report, note, and test file contain no em dashes and no trailing whitespace.

I did not run the 391-case or 1,128-case suites, as instructed.

## Non-blocking observations (no change requested)

- `tests/test_memory_owner_job_processes.py:39`: the new comment says that group signals "can reach" a grandchild after the direct child exits. To be precise, `killpg` queues the signal to all members at once, and the grandchild's exit is what lags. The replaced comment also explained why `Z` counts as stopped, and that explanation is now gone. Both readings lead to the same code, so this is wording only.
- If the kernel reused a grandchild PID inside the 5 second window, the assertion could fail falsely. `pid_max` is 4,194,304 on this host, so the risk is negligible. The old assertion had the same exposure.
- The note and the report say "within five seconds", and the evidence supports the tighter figure of 4.18 ms. That is accurate, only conservative.

## Limitations

- I did not inspect the running exact archive run, live servers, or memory, as instructed. Final qualification depends on that run.
- I did not rerun the service-account `/proc` boundary tests or the 12 dashboard mutations. I rely on the prior records.
- I reviewed the round 1 report bundle (`1476f532`) for its claims about this increment only. I did not re-execute its scripts.

## Raw data

- `data.json`: structured results and claim checks.
- `evidence.tar.gz`: the outputs of the individual test runs, the 30 module repeats, the red replay with its variant test file, the mutation replay, and the mutation script.
