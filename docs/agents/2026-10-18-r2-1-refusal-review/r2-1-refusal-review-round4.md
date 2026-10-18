# R2-1 refusal review, round 4

- Date: 2026-10-18
- Role: code reviewer
- Model: Claude Opus 5.5 (claude-opus-5-5)
- Question: Does `git diff 5d746bfc..7a0cba6a` on `feature/minimal-install-review` close round 3 findings M1 to M3? Does the whole feature (`git diff 48bbd0e6..7a0cba6a -- optional tests docs/in-place-installation-design.md CHANGELOG.md docs/verification`) have a remaining blocking defect on the daily, development, and CT 114 layouts, in test isolation, docs accuracy, or coding standards?

Raw data in `raw-round4/`:

- `diff-5d746bfc-7a0cba6a.patch`, `diff-feature.patch`: the reviewed diffs.
- `r4-tests-*.txt`: the requested test runs, a run without a user bus, and `test_release_manager_cli.py`.
- `probe_round4.py`, `probe-round4-output.txt`: the round 3 probe rerun at `7a0cba6a`, plus the development layout with every command on `~/.local/bin/hermes` and single-key refusals. Only `subprocess.run` inside `inplace_services` is replaced; programs and drop-ins are real files and the real `show()` and `parse_show()` run.
- `mutant_round4.sh`, `mutant-round4.txt`: removes one key at a time from `UNIT_COMMANDS` in a scratch copy and runs `TransitionTests`.
- `local-systemctl-show.txt`: real systemd 259 (Fedora 44) output for the full property list on a loaded user unit.

## Tests

| Module | Result |
| --- | --- |
| `test_inplace_preparation.py` | 27 tests, OK |
| `test_inplace_preparation.py`, no user bus (`env -u DBUS_SESSION_BUS_ADDRESS XDG_RUNTIME_DIR=/nonexistent`) | 27 tests, OK |
| `test_inplace_services.py` | 9 tests, OK |
| `test_inplace_plan.py` | 14 tests, OK |
| `test_inplace_worker.py` | 24 tests, OK |
| `test_release_manager_cli.py` | 14 tests, OK |

The test count of `test_inplace_preparation.py` stays 27 because the new cases are subtests in `test_transition_checks_every_command_of_a_unit`.

Mutation check (`mutant-round4.txt`): the unmutated copy passes. Removing any one of the seven keys from `UNIT_COMMANDS` fails `TransitionTests`.

## Round 3 findings

| Finding | Status | Evidence |
| --- | --- | --- |
| M1 stop, reload, condition commands not checked | Closed | `UNIT_COMMANDS` now holds `ExecCondition`, `ExecStartPre`, `ExecStart`, `ExecStartPost`, `ExecReload`, `ExecStop`, `ExecStopPost` (`inplace_preparation.py:72`). Probe: `dev layout, ExecStart repointed, ExecStop/ExecStopPost still on checkout forwarder -> REFUSED`. |
| M2 no `ExecStartPost` test | Closed | Subtest loop over the five added keys; each mutant fails. |
| M3 design section 10 step 4 | Closed | Step 4 now says preparation reads "every start, reload, and stop command" and that a drop-in that sets a command of a replaced gateway refuses. |

Real systemd 259 accepts the seven property names in `--property=` without stderr on every loaded user unit on this host (scan in session; sample in `local-systemctl-show.txt`). It omits empty command properties, which `check_service_launchers` handles. CT 114 (systemd 255) output from round 3 shows the `ExecStop`/`ExecStopPost`/`ExecReload` format, which `_command_programs` parses (`ignore_errors=yes` matches the regex).

## Host layouts

- CT 114 (stock-format gateway replaced, no drop-ins): gateway is exempt, its drop-in list is empty. Dashboard and Pulse have only `ExecStart`, on `~/.local/bin/hermes` and `~/.local/bin/bun`. Probe: accepted. The added keys change nothing here.
- Daily (template units from `release_services.py:43-49`, only `ExecStart`): gateway and dashboard on `~/.local/bin/hermes` (account set), Pulse on `~/.local/bin/bun`, which `release_worker.py:214-215` publishes as a copy of the bun binary (over 1 MiB, so not a forwarder), and `~/.claude/LIFEOS/PULSE/pulse.ts`, which does not name `/.lifeos-releases/` (checked in the LifeOS source). Probe: accepted.
- Development after every command is pointed at `~/.local/bin/hermes` (`ExecStart`, `ExecStop`, `ExecStopPost`; `ExecReload=/bin/kill -USR1 $MAINPID`): probe accepted. `/bin/kill` is small, so it is read, and it does not name the managed runtime.

## Whole-feature pass

- Correctness: `transition_launchers` no longer takes service launchers; no caller or request field still uses `transition_launchers` (grep over `optional` and `tests`). `transition_gateway_unit` runs `check_service_launchers` before it generates the unit, with `replaced=('gateway',)` only when the fragment names `/.lifeos-releases/`, which matches CT 114 and leaves daily and development on the full check.
- Test isolation: `TransitionTests.setUp` patches `inplace_services.show` for every test, and the command tests patch it per call with real `parse_show`. No test in the feature calls the real `systemctl`; the no-bus run passes. `test_release_manager_cli.py` replaces `prepare_inplace` entirely.
- Docs: design step 4, the B1 row, the CHANGELOG line, and the verification README row 9 and the build `80057d6d` rehearsal table match the code. The rehearsal ran before `5d746bfc` and `7a0cba6a`; those commits add only keys that CT 114 does not use outside the replaced gateway, so the record stays valid.
- Standards: ABOUTME headers present in all six touched code and test files and in the raw scripts. Comments describe behaviour. No em dashes or en dashes in the feature diff or in this report.

## Non-blocking notes

- The test comment "Stock Hermes writes its stop commands with the same launcher as the start command." sits above a loop that also covers `ExecCondition`, `ExecStartPost`, and `ExecReload`. The comment explains why, but covers only part of the loop. Style only.
- The refusal message still says "Point the unit at ~/.local/bin/hermes". When the offending command is `ExecStop`, the message names the program path, so the owner can find it. "every command of the unit" would be clearer. Optional.
- Known accepted limits are not re-raised: `$HOME/...` inside shell strings, and the `Exec*` drop-in rule on a replaced gateway.

## Review priorities for Adrian

1. Nothing blocking. The fix is one constant, one doc sentence, and one subtest loop. The probe and the mutation check confirm both directions (refuses a forwarder in each command key, accepts the three host layouts).
2. Not covered by a host run: the stop-command check was not rehearsed on a container. On CT 114 it cannot trigger (gateway replaced). On development it will refuse until `ExecStop` and `ExecStopPost` are repointed as well, which is the intended behaviour. Check with `systemctl --user show hermes-gateway -p ExecStop -p ExecStopPost` on development before the transition.

VERDICT: CLEAN
