# Self-scan review, round 2

- Date: 2026-10-18
- Role: code reviewer
- Model: Claude Opus 5.5 (claude-opus-5-5)
- Question: Review d24b63f6 (`consumer_scan._commands`: a `dashboard`/`serve`/`gateway` word that follows an `--option` without `=` is that option's value) and e0539130 (`inplace_worker.check_reviewed_services`: on apply, compare the sealed plan's roles, created units, and consumers with the worker's fresh `inspect_operation` result before any service stops). Check false negatives on real Hermes command lines, false refusals on legitimate flows, check ordering, tests, and standards.

## Test runs

Raw output is in this folder.

| file | module | result |
|---|---|---|
| rv7-test_consumer_scan.txt | test_consumer_scan.py | 13 tests, OK |
| rv7-test_inplace_worker.txt | test_inplace_worker.py | 25 tests, OK |
| rv7-test_inplace_services.txt | test_inplace_services.py | 11 tests, OK |
| rv7-test_inplace_plan.txt | test_inplace_plan.py | 14 tests, OK |
| rv7-test_release_dashboard.txt | test_release_dashboard.py | 8 tests, OK (1 skipped) |
| rv7-role-probe.txt | `_role` probe on real Hermes command lines | see section 1 |

## 1. `_commands` on real Hermes command lines

Hermes accepts `--profile`/`-p` before the subcommand. `main._scan_profile_flag` pre-parses it, and `_apply_profile_override` strips it from `sys.argv`. `/proc/<pid>/cmdline` keeps the original words, so the scan sees them.

The probe results (rv7-role-probe.txt):

- `python3 -I -c <code> dashboard --host 0.0.0.0` (stock launcher, `runtime_command`): dashboard. `-c` is a short option, and the code word does not start with `--`.
- `hermes -p work serve --port 9200 --host 0.0.0.0` (named-profile relaunch, `web_server_profiles` uses `-p`): dashboard.
- `hermes --profile work gateway run --external-supervisor` (gateway unit, `_profile_arg` writes `--profile <name>`): gateway. `work` is the value, and `gateway` follows a non-option.
- `hermes --profile=work dashboard`: dashboard.
- `hermes gateway --accept-hooks run`: gateway. `run` is still a plain membership test.

False negative (non-blocking): a top-level boolean long flag directly before the subcommand. `_parser._add_top_level_flags` defines `--yolo`, `--accept-hooks`, `--safe-mode`, `--ignore-user-config`, `--ignore-rules`, `--worktree`, `--no-restore-cwd`, `--pass-session-id`, `--tui`, `--cli`, `--dev`, `--native`, `--version`, and `--continue` (optional value). Two of them are plausible on a hand-started gateway. `gateway/run_startup.py:1106` says that the gateway has no TTY, so hook consent must come from `--accept-hooks`. `--yolo` approves commands without a prompt. The probe shows that `hermes --accept-hooks gateway run` and `hermes --yolo gateway run` now classify as `other`. Before d24b63f6 they classified as `gateway`.

Consequence: `inventory` puts that gateway in `blocking`. Preparation refuses with "Close these Hermes processes before the operation: ...", and it does not offer a gateway unit. The result is a safe refusal with a clear action. Nothing stops, and nothing is lost. I do not consider it blocking. A small fix is to skip the value rule when the preceding word is one of Hermes's top-level boolean flags. The plugin could also derive the value-taking set from `hermes_cli._parser.top_level_value_flag_sets()`, but that covers only top-level options, so `lifeos-release prepare --name dashboard` would still need the current rule. A test for `--accept-hooks gateway run` should go with the fix.

No Hermes dashboard launcher that I found puts a boolean flag before `dashboard` or `serve`. `relaunch.build_relaunch_argv` puts inherited flags before the subcommand, but no caller relaunches into `dashboard`, `serve`, or `gateway`.

## 2. `check_reviewed_services` on legitimate flows

Placement: in `_run`, after `validate_plan` and `inspect_operation`, and before `services_for`, the mount environment, `ProgramTransaction`, and any `write_state`, drain, or stop. `inspect_operation` (format 2, `inspect_inplace`) raises on `blocking` before the check, so a consumer that is blocking in the worker view refuses at the same point as before. The check runs only for `apply`; recovery and restore skip it. `inplace_worker.run` is reached only for format 2, and `inspect_inplace` always returns a services dict, so the `None` branch is defensive.

Flows:

- Dashboard-driven apply with a hand-started dashboard. `apply_release` re-runs `review_operation` in the dashboard and seals the plan, then launches. The dashboard counts itself (64e6056d). The release worker, in its own transient unit, sees the same dashboard with the same PID, start time, and role. Equal.
- Dashboard-driven apply with a unit-bound dashboard. Both views exclude its control group. Equal.
- CLI `start` without re-review (`cli.launch` does not reseal). The plan comes from preparation. The preparation worker's ancestors (the CLI, a shell) are `other` and are operators there. In the worker they are not consumers of the source unless they are Hermes processes. A Hermes `chat` ancestor is blocking in the worker, and `inspect_operation` raises first. Otherwise equal.
- CT 114 managed-to-in-place transition. All three units are loaded in both views, so `roles` match. Preparation writes the transition gateway unit only into the job directory (`transition_gateway_unit`), and `host_entries` publishes it after the check. The managed gateway and dashboard run in bound groups, which both views exclude. Equal.
- Gateway MainPID change between review and apply. The bound gateway's control group stays the same, so both views exclude it. `active` and `enabled` are not compared. No refusal.
- Update with no consumers: `[]` in both views. Fresh install: both add `pulse` to `created`, because `installed.exists()` has not changed. Equal.

Intended refusals that change behaviour: a hand-started dashboard or gateway that the plan offers, and that restarted or exited between the seal and the worker, now refuses before drain. Before this commit, a restart raised in `replace_with_units` after drain and rolled back. An exit was skipped silently, and the worker still created the unit. The exit case is now stricter. For example, an owner prepares from the CLI, closes the hand-started dashboard, and runs `start`; the worker refuses and asks the owner to prepare again. That is correct, because `created` from the reviewed plan no longer matches the host. Through the dashboard, a second apply reseals and succeeds.

Pre-existing race, not caused by this commit: a short-lived Hermes subprocess that references the source can be alive during either scan, for example `systemd-run` (its argv names `host_python(source)`) or a gateway status subprocess that the dashboard starts. Such a process is `other`, so `inspect_operation` raises before the new check.

## 3. Tests

- `ConsumerRoleTests` adds three cases: `--name dashboard`, `--title gateway run`, and `-p default serve`. `DashboardOptionTests` adds `--name dashboard --host ...` returning `{}`. These cover the intended rule. No case covers `--profile <name> gateway run`, `--option=value dashboard`, or a boolean flag before the subcommand (the gap in section 1).
- `ReviewedServicesTests` tests the pure function. It covers equality, `None`/`None`, and differences in `created`, `roles`, removed consumers, `None` against a dict, and a changed start time. It does not show that the comparison ignores `command`, `active`, `enabled`, `signature`, or list order. It does not cover a changed PID or role. No test drives `_run` to show that the refusal comes before any stop. The call site is two lines, so I accept that by reading.

## Standards

ABOUTME headers are present and unchanged. The names (`_commands`, `check_reviewed_services`, `identity`) are clear. The docstrings describe current behaviour, with no history. The CHANGELOG line matches the file's style. The diffs contain no em dashes (grep count 0).

## Findings summary

No blocking findings.

Non-blocking:
1. `hermes --accept-hooks gateway run` and `hermes --yolo gateway run` now classify as `other`, so preparation refuses instead of offering a gateway unit. This is a safe refusal and a small regression. Fix: skip the value rule after Hermes's top-level boolean flags, and add a test.
2. The tests do not show that `check_reviewed_services` ignores `command`, `active`, `signature`, and list order. No test drives `_run` to show the refusal comes before a stop.
3. The refusal text says "prepare the operation again". On the dashboard path, a second apply reseals and is enough. The text is accurate for the CLI path and conservative for the dashboard.

VERDICT: CLEAN
