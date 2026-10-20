# R2-1 refusal review, round 2

- Date: 2026-10-18
- Role: code reviewer
- Model: Claude Opus 5.5 (claude-opus-5-5)
- Question: Do commits 80057d6d and adaa6b8a (`git diff 36615439..adaa6b8a` on `feature/minimal-install-review`) close the round 1 findings of `r2-1-refusal-review.md`? Do they add defects (false refusals on the development, daily, or fresh hosts; parsing of `systemctl show` output with several ExecStart entries or arguments with ` ;`)? Are the mocks, the docs, and the coding standards acceptable?

Raw data in `raw-round2/`:

- `r2-tests-test_inplace_*.txt`: the three requested test runs.
- `systemctl-show-real.txt`: real systemd 259 output for units with two ExecStart entries and with ` ;` in arguments.
- `probe_round2.py`, `probe-round2-output.txt`: `check_service_launchers` driven through the real `inplace_services.show` parser. Only `subprocess.run` is replaced, and the files are real.
- `mutant_round2.py`, `mutant-round2.txt`: wiring mutations.
- `host-systemctl.txt`, `tests-without-user-bus.txt`: the test suite reaches the real user service manager.

## Tests

| Module | Result |
| --- | --- |
| `test_inplace_preparation.py` | 24 tests, OK (the permission test ran, not skipped) |
| `test_inplace_plan.py` | 14 tests, OK |
| `test_inplace_services.py` | 8 tests, OK |

The same `test_inplace_preparation.py` run without a user bus (`XDG_RUNTIME_DIR=/nonexistent`, no `DBUS_SESSION_BUS_ADDRESS`): 1 failure, 3 errors. See finding N1.

## Round 1 findings

| Round 1 | Status | Evidence |
| --- | --- | --- |
| F1 shlex errors pass | Closed | systemd parses the unit. A loaded unit with no `path=` refuses (probe: `loaded with ExecStart empty -> REFUSED`). |
| F2 `ExecStart = `, `%h`, shared drop-ins, `\|` prefix, other search paths | Closed | `systemctl --user show` reports the effective command after all of these. CT 114 confirms `%h` in a drop-in. |
| F2 `/bin/sh -c` wrappers | Partly closed | An unquoted absolute forwarder before the first ` ;` refuses. A forwarder after ` ;`, in quotes, or as `$HOME/...` passes (finding N3). |
| F3 all of `~/.local/bin` exempt | Closed | Only `hermes`, `hermes-agent`, `hermes-acp` are exempt. Test covers `hermes-dev`. |
| F4 no wiring test | Closed | `test_transition_gateway_unit_checks_the_other_units` fails when the call is removed (`mutant-round2.txt`). The `replaced` argument is not tested through `transition_gateway_unit` (N4). |
| F5 CT 114 not recorded | Closed | `docs/verification/2026-10-17-inplace-e2e/README.md` has the table and corrects the old sentence. No raw transcript of that run is committed (info). |
| F6 unreadable program traceback | Closed | `_runs_managed_runtime` raises `ReleaseRejected`. Test covers it. |
| F6 bare file name | Closed | systemd reports an absolute `path=`. |
| F6 symlink false refusal, Pulse message nit, behaviour note | Unchanged | Still harmless. The Pulse message still says "Point the unit at ~/.local/bin/hermes". |

## Host layouts

- Daily (template units on `~/.local/bin/hermes`, Pulse on `~/.local/bin/bun`): the gateway unit file has no `/.lifeos-releases/`, so it is not replaced and is checked. All three commands pass: the account launcher is exempt, and bun (2 MiB stand-in, 88 MB real) is over the 1 MiB limit. `pulse.ts` (47 to 49 KB in the repository copies) does not contain `/.lifeos-releases/`. Probe: `daily-like template units ... accepted`. No false refusal.
- Development after the owner repoints the units at `~/.local/bin/hermes`: passes. Before that, refuses, as intended.
- 114 (stock-format managed gateway unit): the gateway role is skipped because preparation replaces it. The rehearsal applied.
- Fresh host: not in transition mode, so the check does not run.

## Findings

### N1 (Medium, blocking) Four existing tests now query the real user service manager

`optional/lifeos_release_manager/inplace_preparation.py:132` and `tests/test_inplace_preparation.py:114, 136, 172-192`. `transition_gateway_unit` now calls `check_service_launchers`, which calls the real `systemctl --user show`. Only the new tests mock `show`. The older tests `test_transition_gateway_unit_is_the_stock_generated_definition`, `test_transition_without_a_gateway_unit_replaces_no_unit`, `test_transition_keeps_a_gateway_unit_that_runs_the_account_launcher`, and `test_transition_refuses_a_managed_unit_whose_kill_mode_differs_from_stock` (through `_generate`) do not. Their result now depends on the units of the account that runs the suite.

Scenarios:

1. Without a user bus (for example `pct exec 114 -- su - lifeos-hermes`, or an SSH session without `XDG_RUNTIME_DIR`), `show` raises "The owner service manager does not report ...". The run fails with 1 failure and 3 errors (`raw-round2/tests-without-user-bus.txt`).
2. On the development host before the owner repoints the units, `hermes-dashboard.service` runs `~/workspace/hermes-agent/.hermes/bin/hermes`, a managed forwarder. The tests then raise the R2-1 refusal, and the KillMode test gets the wrong message.
3. On any host with a loaded unit whose program is unreadable, the tests fail the same way.

This host passes only because all three units are `not-found` here (`raw-round2/host-systemctl.txt`). Fix: patch `inplace_services.show` (for example to report `not-found`) in those tests, or in a `setUp` for `TransitionTests`.

### N2 (Low) Only the last ExecStart line is checked

`optional/lifeos_release_manager/inplace_services.py:23`. systemd prints one `ExecStart={ ... }` line per entry (`raw-round2/systemctl-show-real.txt`, `flatpak-add-fedora-repos.service`). `show` builds a dictionary, so the last line wins. Scenario: an owner makes the dashboard `Type=oneshot` with two ExecStart lines and the forwarder in the first. Preparation accepts it (probe: `oneshot, forwarder in first of two ExecStart lines -> accepted`). systemd allows only one ExecStart for `simple`, `exec`, and `notify`, and all generated and stock units use those types. No known host has this layout. `ExecStartPre` and `ExecStartPost` are not checked either.

### N3 (Low) Shell wrappers are covered only partly

`optional/lifeos_release_manager/inplace_preparation.py:107`. systemd prints `argv[]` joined with spaces and without quotes, so an argument that contains ` ;` ends the non-greedy `(.*?) ;` match early (`raw-round2/systemctl-show-real.txt`, `nfs-server.service`). Probe results: `/bin/sh -c "true ; exec <forwarder>"`, `exec '<forwarder>'`, and `exec $HOME/.../hermes` are accepted. `exec <forwarder> ; true` refuses. No known host uses a shell wrapper, and a complete shell parse is not practical. Matching up to ` ; ignore_errors=` instead of the first ` ;` closes the first case cheaply. The others need a decision that shell wrappers refuse, or acceptance of the gap.

### N4 (Low) The replaced gateway skips its drop-ins, and the `replaced` wiring has no hermetic test

`optional/lifeos_release_manager/inplace_preparation.py:98, 131-132`. When the gateway file names `/.lifeos-releases/`, the gateway role is skipped completely. The text loop at lines 125-128 refuses a drop-in only when its text names `/.lifeos-releases/`. Scenario: a managed gateway unit has an owner drop-in `hermes-gateway.service.d/override.conf` with `ExecStart=` and `ExecStart=%h/workspace/hermes-agent/.hermes/bin/hermes gateway run`. Preparation accepts it. The transition replaces the main file. `adopt_definition` keeps drop-ins, so the gateway still runs the forwarder, which is the R2-1 failure. No known host has this drop-in, so this is Low. Also, a mutation that always passes `replaced=()` fails no test on this host, because the gateway is `not-found` here. Only the 114 rehearsal covers that path.

### N5 (Info)

- A unit file edited without `daemon-reload` is checked in its loaded state. If the owner repoints the unit and forgets the reload, preparation keeps refusing with the same message. The message could add "reload the user manager".
- `\bpath=` also matches inside an argument such as `--path=/x`. This only adds checks. A small data file argument that names `/.lifeos-releases/` refuses (probe: `notes.txt`). No known unit passes such an argument.
- `SERVICE_UNITS` (`inplace_preparation.py:69`) and `inplace_services.UNITS` list the same units twice. `import re` is local to the function. Style only.
- The test mock `_show` returns a dictionary, so it bypasses the real `show` parser. Mocking the service manager is acceptable: it is the external boundary, and file checks and argv parsing stay real. A fixture that returns raw `systemctl` text through `subprocess.run` would also cover N2 and N3.

## Docs and standards

- Design section 10 step 4 matches the code, including the exception for a replaced gateway unit.
- The CHANGELOG line matches. It omits that a directly managed gateway is replaced, not refused, but the design covers that.
- The verification README item 9 and the 114 table match the brief's evidence.
- ABOUTME headers are present. The names are clear. The comments describe behaviour, not history. The diff contains no em dashes or en dashes.

## Review priorities for Adrian

1. N1: make the four older transition tests hermetic. This is a small change, and the test run without a user bus verifies it.
2. N3 first case and N4: decide whether to close them now. Each needs a few lines and one test.

VERDICT: NOT CLEAN
