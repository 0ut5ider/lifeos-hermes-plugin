# PR38 review, round 3

- Date: 2026-10-16
- Role: independent reviewer (Claude Code, single agent, no delegates, no memory or journal calls)
- Model: Claude Opus 5.5 (`claude-opus-5-5`)
- Question: Does the final increment `70fa8390..03d6f486cb2427941af9919f1742a5e6183c7e5c` correct the test comment, keep the documentation honest, keep the deployable runtime bytes identical to candidate `70fa8390`, and leave any round 1 or round 2 objection open?
- Range: base `455154c1`, round 1 CLEAR at `99e18c44`, round 2 CLEAR at `70fa8390`, current head `03d6f486`.

## Verdict

**CLEAR.** I found no actionable defect in this increment. No objection from round 1 or round 2 remains open.

## Scope of the increment

`03d6f486` has one parent, `70fa8390`. It changes five files:

1. `docs/agents/2026-10-16-pr38-review-r2/pr38-review-r2.md`, `data.json`, and `evidence.tar.gz` (the round 2 record).
2. `notes/2026-10-16-process-exit-observation.md` (one sentence replaced by three).
3. `tests/test_memory_owner_job_processes.py` (one comment line replaced by two).

No other path changes.

## Test comment

The new comment at `tests/test_memory_owner_job_processes.py:39-40` reads:

```
# SIGKILL is queued to the whole group; a grandchild can exit after its parent.
# A killed grandchild can await the operating system's parent reaper.
```

1. The first line matches the round 2 observation: `killpg` queues SIGKILL to every group member at once, and the grandchild exit is what lags. It is accurate.
2. The second line is byte-identical to the comment at `99e18c44` that explained why the `Z` state counts as stopped. The round 2 objection that this explanation was lost is resolved.
3. The comment states what the code does and why. It contains no history wording.

The Python AST of the file before and after the change is equal (`ast.dump` comparison). Only the comment bytes differ.

## Documentation honesty

The note now says that concurrent source exports overlap with the two quota errors, and that their contribution is plausible but not measured. This matches the evidence: the archive stderr shows `Errno 122` in two health tests, and no measurement attributes the quota use. The qualification repair report (`docs/agents/2026-10-16-pr38-qualification-repair/pr38-qualification-repair.md:5`) already says only that the exports and the run overlap. No active document in the PR now claims a measured cause.

Correction to round 2: the round 2 report says that the repair report attributes the quota errors to the exports. The causal wording was in the note (`put pressure`), not in the repair report. The note is now corrected, so this changes no conclusion.

The changed note, test file, and committed round 2 report contain no em dashes and no trailing whitespace. `git diff --check 70fa8390 03d6f486` is clean.

## Runtime byte equivalence

`scripts/build_managed_release.py:29` packages `lifeos_hook_bridge`, `optional`, `scripts`, `tests`, `docs/deployment/daily-text`, `VERSION`, `CHANGELOG.md`, `README.md`, and `docs/verification/2026-10-11-daily-guest/deliver_morning.py`. Between `70fa8390` and `03d6f486`, `git diff --stat` over these paths shows only `tests/test_memory_owner_job_processes.py`. The tree objects of `lifeos_hook_bridge`, `optional`, and `scripts`, and the `VERSION` blob, are identical.

Therefore the claim in the brief is correct: deployable runtime bytes are identical, and the only packaged difference is the non-executable comment in one test file. The packaged tracked files are not all byte-identical, and the certificate must not claim that. The package directory name also contains `head[:8]`, so packages built from the two commits have different names. The certificate plan to state both commits covers this.

## Prior objections

| Source | Item | Status |
|---|---|---|
| Round 1 | No defect | Nothing reopened |
| Round 1 N1 to N3 | Informational | Unchanged by this increment |
| Round 2 | Comment wording and lost `Z` explanation | Resolved |
| Round 2 | Quota cause stated as a cause without proof | Resolved in the note |
| Round 2 | PID reuse risk, conservative "five seconds" figure | Informational, unchanged, no action needed |

## Non-blocking observation

The comment sits above `if state == 'Z'`. Its first line explains the polling loop more than the `Z` check, and in `test_stop_assertion_waits_for_actual_process_exit` the polled process is a direct child, not a grandchild. The code and the test are correct. This is placement only, and I request no change.

## Tests I ran

Interpreter: `/home/outsider/.cache/lifeos-daily-promotion-20261014/frozen-test-environment/bin/python` with `-B -W error::ResourceWarning`, `PYTHONPATH=<export>:<export>/tests`, `TMPDIR=~/.cache/pr38-r3/tmp`, on a `git archive` export of `03d6f486` (`lifeos_hook_bridge`, `tests`).

1. `test_memory_owner_job_processes`: 3 tests, 3 pass, 1.802 s. No `time.sleep(60)` process remained afterward.
2. My first attempt failed with `ModuleNotFoundError` because I omitted `PYTHONPATH`. That was my invocation error, not a test result.
3. AST equality check of the test file before and after: equal.
4. Tree and diff comparison of all packaged paths (see above).

I did not run the 391-case or 1,129-case suites or the 30 process repeats, as instructed.

## Limitations

- I did not inspect the active archive run of `70fa8390`. Qualification still depends on its result.
- I did not re-execute the round 1 or round 2 evidence scripts.
- I did not run a live server, memory, journal, credentials, or another agent CLI. I made no Git staging, commit, or product or test edits.

## Changes outside Git

Scratch directory `~/.cache/pr38-r3/` (test export and copies of the two test file versions). Remove it with `rm -rf ~/.cache/pr38-r3`.
