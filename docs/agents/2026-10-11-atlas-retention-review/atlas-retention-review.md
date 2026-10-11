Date: 2026-10-11

Role: Independent reviewer, Cerebo, delegated review only.

Question: Does the Atlas history retention implementation preserve the required admission, ownership, provenance, accounting, capacity, and grouped recovery behavior before a pull request?

Model: GPT-6, through the Codex harness. The session identifies the model as GPT-6; the precise serving variant is not exposed to this reviewer.

Reviewed branch: `feature/atlas-history-retention`.

Reviewed HEAD: `72b0d4a2aaf7b1d7cf07e7bd7a16e078cf019388`.

Reviewed base: `c9fdf51ca92c937a4d01e5c7903cf659a1e46552`.

Adrian, I found no release blocker and no confirmed correctness or ownership regression in the reviewed change. The focused suite passes all 22 cases. Two additional real-native checks pass. The review does not establish that every possible filesystem or process race is safe.

I reviewed the changed history, sync, access, service, and CLI code, the new retention tests and process helper, and the changed capacity and command-registration tests. I followed the existing transaction journal, graph admission, source collection, retirement checks, scope resolution, and final service authority check. I read the installed native Atlas store, synchronization planner, collectors, and dashboard source. The evidence directory contains the exact diff, the inspected source with line numbers, and the corresponding source hashes.

The implementation trims an in-memory copy only after `_snapshot` admits the existing graph and sources. `memory_atlas_sync.py:84` sends the retained bytes through the actual native planner. `memory_atlas_history.py:78` preserves the requested recent run window, each collector's maximum identifier, each collector's maximum completion timestamp, and both observation tables' run references. `memory_atlas_history.py:85` counts removed runs and successes before deletion. `memory_atlas_history.py:103` adds those cumulative counts to the next native public snapshot. I found no path that deletes an asset or observation to make a capacity check pass.

The archive binds exact prior database and snapshot bytes to a canonical manifest. The manifest includes the expected new output hashes, removal counts, current scope signature, retirement digest, and source digests. `memory_atlas_history.py:160` checks the archive identifier, canonical manifest bytes, and both prior file hashes before reading rows. The fixed table selection and SQLite parameter for the offset keep archive queries bounded to 100 rows per page. The archive path resolver rejects symlinks, hard-linked files, non-owner files, and shared permissions.

The archive and live graph use the same expected-digest recovery journal. `memory_atlas_sync.py:154` checks current authority before each write and publishes the three archive files before the two live files. The current source and output checks precede the committed receipt. The existing recovery code checks all expected destinations before restoring the group and refuses a later artifact edit. The five real subprocess termination boundaries pass. The later archive edit test retains both the changed file and the pending journal.

Archive reads reuse unrestricted owner admission and the current retirement filter. `memory_service.py:261` checks current authority again after the native operation returns, which covers configuration changes during the archive reread. The tests verify revoked ownership, disabled CLI ownership, changed archive bytes, changed provenance, arbitrary path and table inputs, and retired text. These tests use actual native code, real temporary files, actual Bun and Python subprocesses, and the actual Hermes command. Observation hooks in existing tests inject real filesystem or configuration changes; the checks do not replace native reconciliation with mocked results.

The primary reviewer supplied the previously completed local and isolated `.252` 106-test receipts. I inspected their recorded commands, successful exit codes, durations, and unchanged-source flags. I treated them as supporting evidence and ran the focused checks independently. I did not rerun the remote suite or touch either live guest.

| Verification | Result | Evidence |
| --- | --- | --- |
| Retention module plus capacity test class | 22 tests pass in 86.602 seconds; no skipped tests; implementation hashes unchanged | `focused.json`, `focused.stderr`, `focused.done` |
| Additional protected-only capacity fallback | Pass; selected window is 0 runs / 0 events; graph has 9,978 of 10,000 fields; referenced run 2 and latest gear run 4 remain alongside new runs 5 and 6; all 252 assets remain | `additional-cases.py`, `additional-measurements.json` |
| Additional mixed success and partial-run accounting | Pass; gear totals progress from 65 runs / 23 successes to 66 / 24 and then 131 / 25; Projects totals progress from 1 / 1 to 2 / 2 and then 3 / 3; the 2099 maximum timestamp remains | `additional-cases.py`, `additional-measurements.json` |
| Additional runner | 16 tests pass in 67.573 seconds. It runs the two new cases and also discovers 14 existing retention cases through the imported fixture class | `additional-execution.json`, `additional.stderr`, `additional.done` |
| Whole-diff whitespace check | Returns 2 for nine trailing-whitespace lines in the historical `development-harness-development.stderr` receipt | `whitespace-checks.json` contains the complete output |
| Implementation, tests, and authored documentation whitespace check | Pass, exit code 0 | `whitespace-checks.json` |
| Tracked checkout state | Clean after the review; only permitted review artifacts were written | `git-evidence.json` |

No finding requires an implementation change. The whole-diff whitespace result concerns retained raw test output and does not indicate a runtime defect. I left that evidence unchanged.

The practical limits are process termination rather than host power-loss testing, synthetic inventories rather than personal data, and selected local coverage rather than a new daily-release acceptance run. The focused checks cover the five completed writes and the grouped restore behavior. They do not stress every filesystem race between path validation and publication, every storage failure, or large collections of archive directories. I did not find a reproducible regression in those untested cases.

The default 32-run and 64-event windows, the smaller capacity windows, indefinite archive retention, and a future whole-guest backup restore remain the documented policy. A new whole-guest Proxmox Backup Server restore and the daily release deployment are later release work. Their absence from this development review is not a blocker. The changed file inventory shows no native patch, pin, model map, schedule, or dependency change.

The remaining review attention belongs to release acceptance: include the complete external Atlas history and pending governance journals in the guest backup, preserve the reviewed source and executable modes in the release package, and test that release as one unit. I made no implementation or test change, no commit, no push, no pull request, and no live-server change. The only changes outside tracked Git content are disposable scripts and evidence under this review directory.
