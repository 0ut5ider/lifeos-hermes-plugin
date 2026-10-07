Date: 2026-10-07
Role: Read-only targeted PR #4 retry and admission closure reviewer
Question: Do the last two review findings remain reproducible at the pushed head, and do their corrections introduce adjacent root or account-admission failures?
Model: Inherited gpt-6.1-sol according to the parent agent's live catalog. The reviewer does not have a separate runtime model identity query.

Reviewed head: `564ea994d03450dd454764406b5f144021c8a645`.
Branch: `feature/selection-recovery-fixes`.
Comparison: `e7c10d02f2e4385bcea76e9dc0880aabb962c3f3..564ea994d03450dd454764406b5f144021c8a645`.

No findings in the bounded scope. I recommend merging this head for the retry and admission corrections. This recommendation does not establish complete installed-host release acceptance or certify the entire PR3/PR4 history.

I independently ran the five requested narrow modules. The run reports **50 tests and 20 subtests passed**, with no skips, warnings, or stderr output. Exit status is 0. The detached process used `setsid`, and its `.done` marker exists. These counts cover this reviewer's run only. The primary agent's 65-test gate includes additional evidence modules and is a separate, overlapping run.

The first finding is closed in the paths reviewed. `installation_selection._roll_back` invokes `recover_mount(target, previous)` on every attempt that requires remounting. The `target_mount_recovered` field records progress and does not skip later validation. `MountTransaction.for_selection` resolves the active native journal only within the target and previous installed roots. `_recover_mount` then uses regular transaction status/recovery and calls `check_completed` on each compensation attempt. Matching completed journals check the exact digest and mode for their committed or restored files before compensation restores the profile setting or remounts.

The real native tests execute Bun mounting and Hermes configuration checks. Child processes exit after a target native commit, after the compensation checkpoint, after clearing the previous setting, and after the previous native commit. Later SOUL edits survive two refused retries, and service start and verification callbacks do not run. Matching positive controls restore the exact previous SOUL bytes. The existing pending previous-root recovery test also passes, so resolving the previous active journal does not attempt to recover the target journal instead.

The second finding is closed in the paths reviewed. `_selection_job_status` releases queued/running/recovering admission only after a successful, complete `systemctl show` query reports `ActiveState=inactive` or `failed` and an empty `Job`. A stopped job with no transaction journal is observed as failed, so a launcher failure no longer permanently blocks new admission. A stopped job with an unfinished transaction journal remains interrupted. Active and transitioning states, queued jobs, failed or incomplete queries, a missing controller, and an actual controller timeout preserve pending admission. The account coordination lock still covers scan, request creation, and launch; the worker still takes that account lock before service access.

The failed-launch regression uses a real local launcher process that exits 23, confirms a stopped unit through the local controller fixture, then admits a new job. The concurrent two-profile test still admits exactly one request. The worker account-lock test still passes. These are controlled transport processes and service recorders, not live systemd worker or gateway acceptance tests.

Additional reviewer probes confirm the adjacent guards:

| Probe | Observed result |
| --- | --- |
| Matching target journal | Accepted, SOUL unchanged |
| Active journal at a third installation | Refused, SOUL unchanged |
| Journal for another profile | Refused, SOUL unchanged |
| File entry outside the allowed profile/baseline targets | Refused, SOUL unchanged |
| Workspace outside the selected workspace and installed home | Refused, SOUL unchanged |
| Public journal or mount-state permissions | Refused, SOUL unchanged |
| Matching account workspace after clearing selection | Accepted, SOUL unchanged |
| Later SOUL edit after clearing selection | Refused, later edit unchanged |
| Inactive/failed unit with empty Job and no journal | Observed failed, stored queued status unchanged |
| Active, activating, deactivating, reloading, maintenance, refreshing unit | Observed queued, stored queued status unchanged |

The unchanged authority refusal tests pass for revoked owners, another physical profile, another journal profile, invalid request profile aliases, and selected/configured roots outside the interrupted selection journal. `for_selection` uses `_read` for the initial journal read and then the ordinary `_manifest` path for transaction work. The new workspace exception matches the account workspace derived for the physical profile after clearing the setting. It does not bypass digest checks, owner profile checks, private journal/state checks, or allowed file-target validation in the paths exercised.

I also inspected the existing completed foreign-baseline behavior in `_manifest`: a completed journal for a different baseline returns no applicable manifest. That behavior predates this comparison. Selection mounts and compensation derive the same default baseline from the installed root, and the dashboard derives its baseline from the LifeOS home. I did not demonstrate a normal selection path or an introduced regression from that existing behavior, so it is not a finding here. Deliberate explicit mounts retain their existing opt-out from completed fingerprint checking.

Evidence files:

- `inspection-0.json`: starting Git status, command, stdout/stderr, and exit status.
- `inspection-1.json`: exact starting head.
- `inspection-2.json`: full reviewed source/test diff.
- `source-snapshots.json`: current source and narrow test modules.
- `run-narrow-tests.sh`, `launcher.json`, `launcher.stdout`, `launcher.stderr`: exact test command, environment, and detached launch record.
- `narrow-tests.stdout`, `narrow-tests.stderr`, `narrow-tests.exit`, `.done`: completed independent gate.
- `guard-probes.py`, `guard-probes-run.json`, `guard-probes.stdout`, `guard-probes.stderr`: complete supplementary probe source, command/environment, outputs, and exit status. All 17 supplementary probe cases pass. These cases are not included in the pytest count.
- `final-state.json`: final Git head and status plus evidence assertions.

I loaded the coding-rules skill before review. No repository-local or intermediate parent AGENTS.md file was present in the checked project path. I changed no implementation, test, or tracked documentation file, committed or pushed nothing, and called no external communication, service mutation, memory, or journal tool. I wrote only this review's evidence directory.

Adrian's review should focus on the boundary before every compensating remount and the conservative stopped-worker admission rule. Live gateway, dashboard, and Pulse behavior remains outside this review. No deployment or external configuration change occurred.
