# PR18 release UI review, round 9

Date: 2026-10-13
Agent role: Independent code reviewer
Question: Does the native child-routing fixture drain pending agent-close logs correctly, without changing production behavior?
Model: gpt-6.1-sol
Reviewed commit: `f6c47dec41779635778027a38d508583724d63a1`
Comparison commit: `307753c599a665dd11f94c239cfe89aa4dc0816d`
Inspected Hermes upstream commit: `71d34bad1045610252eda02ee79549436896e784`

## Result

No actionable defect found in the bounded delta. The cleanup change is suitable for the next sealed qualification run. This review does not establish full release qualification.

The delta contains two identical patch changes and one engineering note. Each patch adds one import and one call to the native child-routing test. No production hunk changes in this delta.

The fixture closes the child and parent, then calls `flush_log_queue()` inside the temporary `HERMES_HOME` scope. The temporary directory remains present during this call. Hermes implements this function by stopping and joining its queue listener, then restarting the same listener. Pending records therefore finish before directory cleanup starts. The call does not disable asynchronous logging, suppress an assertion, ignore a cleanup error, or change model and effort assertions. This is normal test cleanup, not a hard-exit path; the upstream function explicitly directs hard-exit callers to a separate bounded drain.

## Inspected measurements

I read and parsed the existing controlled traces and runner output. I did not rerun their native tests.

The original trace records a held close-log writer, removal of `agent.log`, entry into removal of `logs`, and reopening of `agent.log` by the listener. The associated output reports `OSError: [Errno 39] Directory not empty`, seven passes, and one failure. Its receipt is exit 1 and stderr is empty.

The fixed trace records `explicit-drain`, then completion of the held writer, before removal of `agent.log` and `logs`. Its output reports eight passes and zero failures. Its receipt is exit 0 and stderr is empty. Audit events record entry into filesystem calls, so the trace alone does not establish their return times. The traceback and runner receipts supply the failure and success outcomes.

The earlier sealed native output reports 715 passes and one failure across 38 files. The failure is this fixture's temporary-directory cleanup. I did not treat that failed gate as successful qualification.

## Independent read-only checks

1. `git diff 307753c5..f6c47dec` confirms the fixture-only scope.
2. SHA-256 and exact byte comparison confirm that both patch copies are identical.
3. A parser checks all eight patch hunks. Every declared old and new line count matches the patch body. The added test-file hunk contains 147 new lines.
4. Python `ast.parse` accepts the test source extracted in memory from the new-file hunk.
5. `git apply --numstat patches/hermes-child-routing.patch` succeeds. It reports 147 test-file additions and 64 additions with nine deletions in the existing production delegate patch.
6. `git apply --check` succeeds against the inspected upstream checkout. This command does not apply the patch or write the upstream checkout.
7. The inspected upstream `AIAgent.close()` and `flush_log_queue()` implementations support the cleanup ordering described above.

Exact command arguments, working directories, return codes, stdout, and stderr are in `commands.json` and `command-*.stdout`/`command-*.stderr`. `patch-validation.json` records all eight hunk counts. `trace-summary.json` records relevant events in order. Original controlled traces, output, and receipts are copied into this report directory. `source-excerpts.txt` retains the inspected cleanup implementation.

## Exact source hashes

| File | SHA-256 |
| --- | --- |
| `patches/hermes-child-routing.patch` | `be9cb0996267a4b8474aa8862fcd3d3168e68a0253dbe36287a125409d2ff08b` |
| `lifeos_hook_bridge/patches/hermes-child-routing.patch` | `be9cb0996267a4b8474aa8862fcd3d3168e68a0253dbe36287a125409d2ff08b` |
| `notes/2026-10-13-native-log-cleanup.md` | `3d9290764f0ddb0f5f153a4d2c09639e5218055759b410851f1dc7341776aa87` |
| Upstream `hermes_logging.py` | `1b2729b4f25ca130767963ab50aeab9fcb005c88f836ec00a0a20bef71e47de0` |
| Upstream `run_agent.py` | `9fca746dde685859ed084d6f7651a94d8849e8944a145de77f8a177c839cb5ac` |

`inspected-file-hashes.json` also records the hashes of the copied measurement inputs.

## Scope limits and remaining gates

I did not execute the full native or integration gates, access any guest, mutate a sealed source, change configuration, or call memory or journal tools. I made no product edits, commits, or pushes. I wrote only the authorized review artifacts.

The new seal and full qualification gates remain with the primary agent. The queue drain handles records already pending at the cleanup boundary. It does not promise to prevent arbitrary unrelated producers from logging after that boundary. The controlled fixture evidence supports this measured close-log race correction.
