# Self-scan fix review

- Date: 2026-10-18
- Role: code reviewer
- Model: Claude Opus 5.5 (claude-opus-5-5)
- Question: Are c0f4a9d4 (revert of 96661db6) and 64e6056d (the consumer scan counts a dashboard or gateway that runs the scan) correct across every caller, safe for apply while the dashboard is stopped, and adequately tested? Branch feature/minimal-install-review.

## Test runs (raw output in this directory)

| File | Pattern | Result |
|---|---|---|
| rv6-a.txt | test_consumer_scan.py | 13 OK |
| rv6-b.txt | test_inplace_services.py | 11 OK |
| rv6-c.txt | test_inplace_plan.py | 14 OK |
| rv6-d.txt | test_inplace_worker.py | 24 OK |
| rv6-e.txt | test_release_dashboard.py | 8 OK (1 skipped) |
| rv6-f.txt | test_removal_c*.py | 16 run, 1 failure + 1 error: exactly the two known environmental ones (test_exact_running_coordinator_is_admitted, test_running_bun_outside_reviewed_service_groups_refuses; PermissionError on /proc/1708/exe, sshd-session) |

Red check: I copied the c0f4a9d4 tree to ~/agent-scratch/rv6/old, added the new tests/test_consumer_scan.py, and ran it. `test_a_dashboard_that_runs_the_scan_reports_itself` fails there (`'[]' != "['dashboard']"`), so the test detects the bug.

## 1. Callers of source_consumers / inventory

Complete list (grep of optional/):

- `inplace_plan.inspect_inplace` -> `inventory(..., operators=ancestors())`. Runs in three processes:
  - Preparation worker (`release_preparation.queue` uses `subprocess.Popen` from the dashboard, so the dashboard is its parent). Self argv is `python -B release_preparation.py <profile> <job>`, role 'other', so it is skipped as before. The dashboard is an ancestor with role 'dashboard'. The operators filter drops only 'other' ancestors, so the dashboard is counted. This matches the live observation.
  - Dashboard process (`review_release` and `apply_release`, both call `review_operation`, which re-seals plan.json). Before the fix the dashboard skipped itself. Now it counts itself as role 'dashboard'. Its view now matches the preparation worker's view.
  - Release worker (systemd-run transient unit, `_run` -> `inspect_operation`). Self role 'other', skipped. Its ancestors are the user manager. It sees the hand-started dashboard as an offer. No change.
- `inplace_worker._consumers_stopped` -> `inventory(..., excluded_pids={os.getpid()})`. The worker is 'other' anyway. No change.
- `removal_preparation.check_consumers` -> `source_consumers(source, state_directory(source), excluded_groups=groups)` for an in-place removal. Called from `prepare` (twice) and `removal_workflow.execute`. All of these run in the memory workflow coordinator, which `memory_workflow.launch` starts with systemd-run; `removal_consumers.coordinator` verifies `MainPID == os.getpid()` in a transient unit. The coordinator argv is `python -B -c <code> <worker> <job> <action>`, role 'other', so it is still skipped. No dashboard runs this check in-process. The removal path also uses a second scanner, `removal_consumers.processes`, which still skips `os.getpid()` unconditionally; this commit does not touch it.
- host_compatibility, inplace_preparation, release_plan, inplace_removal: no consumer scan.

No path refuses because the calling dashboard now counts itself, except one that already refused in preparation. If a `hermes-dashboard.service` unit is loaded and the owner serves the review from a second, hand-started dashboard, the review now lists the serving dashboard as blocking. The preparation worker (a child of that dashboard) already refused in that case, so the result is the same. The message asks the owner to close the dashboard they are using, which is confusing but correct.

Gateway self: unreachable in practice. The plugin registers only a CLI command and a skill. The gateway never calls inventory in-process. A terminal-tool child of the gateway is 'other', and the gateway is an ancestor that was already counted. The 'gateway' branch of the condition is harmless.

Non-blocking edge: `_role` matches any whole argv word `dashboard` or `serve`. `hermes lifeos-release prepare --name dashboard` (or `--assistant serve`, or `-p dashboard`) now classifies the CLI process itself as a dashboard. When no dashboard unit is bound, the plan then offers and creates `hermes-dashboard.service` that nobody asked for. `replace_with_units` skips the exited prepare process, so nothing breaks; the only effect is an unrequested unit. This weakness already existed for ancestors. It is now reachable for self, but only through a contrived name.

## 2. Dashboard stopped during apply

- The launch is independent of the dashboard. `apply_release` re-reviews, issues the authorization, and calls `commands.launch`. `launch` runs `admit_operation` and then systemd-run, because `plan['services']` is a dict and so truthy for in-place. It then publishes worker-launch.json and returns. The worker runs in its own transient unit and control group, so killing the dashboard does not kill it.
- Admission finishes before the launch. Admission state lives in files, and flock locks are released when the holder dies.
- The SIGTERM comes from `_consumers_stopped`, after the worker has validated admission, run a full `inspect_operation`, and drained services. That takes seconds. The HTTP response and the worker-launch.json publish finish long before it in practice. I found no ordering guarantee, but the window is not realistic.
- Status polling. The page polls every 5 s. While the dashboard is down, the poll `catch` sets "Release status needs an authenticated installation owner." That text is misleading, and nothing clears it on a later successful poll. The action message already says "Refresh this page to check the result." The new unit receives the same --host/--port (11e98e5d), so a refresh reaches it. A restart of a unit-bound dashboard already behaves this way. Non-blocking UX note.

## 3. Can the re-seal still diverge from preparation?

- `ancestors()` differs by process. In the dashboard process it is the dashboard's own ancestors (for example a shell, or a Hermes chat session that started the dashboard through its terminal tool). In the preparation worker it is the dashboard plus those same ancestors. In the release worker it is the user manager. A role-'other' Hermes ancestor of the dashboard is exempt in both preparation and review, but blocking in the worker. The worker's own `inspect_operation` runs before `services.drain` and raises on `blocking`, so it refuses before it changes anything. Safe.
- Recommendation (non-blocking): the worker computes a fresh `selected['services']` and then discards it in favour of `plan['services']`. A check that the fresh `roles`, `created`, and consumer `(pid, start_time, role)` set equal the sealed ones would turn any future divergence into a refusal before drain, with no service stop and no rollback. That check would have caught the 0.8.0-rc.2 failure before it stopped anything. After this fix I found no remaining scenario in which the two views disagree on `created` or the consumers, so this is hardening and does not block.
- The dashboard re-seals at review and again at apply. The owner approves the review result, while the worker applies the plan sealed at apply. This is existing design and is outside this change.

## 4. Revert cleanliness

`git diff 96661db6^ c0f4a9d4` is empty. The revert leaves nothing behind.

## 5. Tests

- The new test starts real subprocesses with PYTHONPATH set when they start. The dashboard subTest proves the scanning process reports itself. The 'chat' subTest proves an 'other' scanning process still skips itself. It fails on the old code (see the red check above).
- Existing `test_excluded_processes_and_this_process_are_ignored`: the `os.getpid()` assertion is vacuous. `os.environ[...] = ...` calls putenv, which does not change `/proc/self/environ` (checked: a probe process set a variable and did not find it in its own /proc/self/environ). The test process never references the temporary source, so the assertion passes with or without self-exclusion. This was true before this commit. The new 'chat' subTest now provides the real coverage. Non-blocking; the dead half could be removed or replaced later.
- Gateway self has no test. It is not reachable (see 1).

## Standards

ABOUTME headers are unchanged and present. The docstring states current behaviour with no history. The CHANGELOG line follows the file's existing release-reference style. No em dashes in either commit (grep count 0). The names are fine. Operator precedence in `not arguments or int(process.name) == os.getpid() and _role(arguments) == 'other'` is correct (`and` binds tighter), but explicit parentheses would read better.

## Findings summary

No blocking findings.

Non-blocking:
1. `_role` word matching lets a CLI argument value `dashboard`/`serve` make the prepare process count as a dashboard, which creates an unrequested dashboard unit.
2. Worker hardening: compare the fresh services inventory with the sealed `plan['services']` before drain.
3. The poll error message while the dashboard restarts is misleading and stays on screen.
4. The vacuous self assertion in the old self-exclusion test.

VERDICT: CLEAN
