# R2-1 refusal review, round 3

- Date: 2026-10-18
- Role: code reviewer
- Model: Claude Opus 5.5 (claude-opus-5-5)
- Question: Does commit 5d746bfc (`git diff adaa6b8a..5d746bfc` on `feature/minimal-install-review`) close round 2 findings N1 to N5? Does it add defects or false refusals on the daily, development, and CT 114 layouts? Is `_check_replaced_drop_ins` (any `Exec` line in a drop-in of a replaced unit refuses) a real false-refusal risk? Do the docs and the coding standards match?

Raw data in `raw-round3/`:

- `r3-tests-*.txt`: the requested test runs, including the run without a user bus.
- `ct114-systemctl-show.txt`: read-only `systemctl --user show` of the three units on CT 114 (systemd 255), including the stop commands.
- `stock-gateway-stop-commands.txt`: `ExecStop`, `ExecStopPost`, `ExecReload` in the pinned stock Hermes `hermes_cli/gateway.py`.
- `probe_round3.py`, `probe-round3-output.txt`: `check_service_launchers` through the real `show()` and `parse_show()`. Only `subprocess.run` is replaced. Programs and drop-ins are real files.
- `mutant_round3.sh`, `mutant-round3.txt`: one source mutation at a time against `TransitionTests` and `ParseShowTests`.

## Tests

| Module | Result |
| --- | --- |
| `test_inplace_preparation.py` | 27 tests, OK |
| `test_inplace_preparation.py`, no user bus (`env -u DBUS_SESSION_BUS_ADDRESS XDG_RUNTIME_DIR=/nonexistent`) | 27 tests, OK |
| `test_inplace_services.py` | 9 tests, OK |
| `test_inplace_plan.py` | 14 tests, OK |
| `test_inplace_worker.py` | 24 tests, OK |

Mutations (`mutant-round3.txt`): the tests catch `replaced=()` always, removal of the drop-in check, the old ` ;` argv regex, no quote stripping, `ExecStart` only, last entry only, and a last-wins `parse_show`. Removing `ExecStartPost` from `UNIT_COMMANDS` passes all tests (finding M2).

## Round 2 findings

| Round 2 | Status | Evidence |
| --- | --- | --- |
| N1 older tests read the real user manager | Closed | `TransitionTests.setUp` patches `inplace_services.show`. The run without a user bus passes. No other test module calls `transition_gateway_unit` or `check_service_launchers`. |
| N2 last ExecStart only; Pre/Post unchecked | Closed for start commands | `parse_show` keeps each repeated line. Probe: `two ExecStart, forwarder in first -> REFUSED`, `dashboard ExecStartPre on forwarder -> REFUSED`. Stop commands are still unchecked (M1). |
| N3 argv stops at first ` ; `, quoted tokens | Closed for the cheap cases | Regex now ends at ` ; ignore_errors=`. Tokens lose surrounding quotes. Probe: `nfs-server style ... -> REFUSED`. `$HOME/...` inside a shell string still passes, which round 2 accepted as a gap. |
| N4 replaced gateway drop-in sets ExecStart | Closed | `_check_replaced_drop_ins`. Hermetic wiring test `test_transition_gateway_unit_checks_the_drop_ins_of_a_replaced_unit`; the `replaced=()` mutation now fails it. |
| N5 daemon-reload hint, duplicate unit lists | Closed | Message adds `systemctl --user daemon-reload`. `SERVICE_UNITS` removed; `transition_gateway_unit` uses `inplace_services.UNITS`. `import re` is at module level. |

`parse_show` change and other callers: `inplace_worker.py:142,155` and `_properties` request only single-valued properties, so the join does not change them.

## Host layouts

- CT 114 (stock-format managed gateway, replaced, no drop-ins): `DropInPaths=` is empty for all three units (`ct114-systemctl-show.txt`). Dashboard runs `~/.local/bin/hermes`, Pulse runs `~/.local/bin/bun`. Probe: `CT 114 layout, gateway replaced -> accepted`. systemd 255 omits empty `ExecStartPre`/`ExecStartPost` and prints no stderr, so `show()` does not raise.
- Daily (template units on `~/.local/bin/hermes`, Pulse on bun, `backup-privacy.conf` with `UMask=0077`, dashboard `daily-text.conf`, Fedora's global `10-timeout-abort.conf`): gateway not replaced, so the drop-in text check does not run. Probe: `daily layout -> accepted`.
- Development after the owner repoints ExecStart: accepted (probe), but see M1.
- `_check_replaced_drop_ins` false-refusal risk: it runs only for a replaced gateway. On the known hosts that is CT 114, which has no drop-ins. A Fedora host adds `/usr/lib/systemd/user/service.d/10-timeout-abort.conf` to `DropInPaths`; it contains only `TimeoutStopFailureMode=abort`, and the probe accepts it. A drop-in with `ExecStop=`, `ExecReload=`, `ExecSearchPath=`, or `ExecPaths=` refuses (probe), even with a harmless target. No known host has one. I judge this not a real risk on these hosts. Comment lines (`#`, `;`) do not match.

## Findings

### M1 (Medium, blocking) Stop commands of a non-replaced gateway are not checked

`optional/lifeos_release_manager/inplace_preparation.py:72` (`UNIT_COMMANDS = ('ExecStartPre', 'ExecStart', 'ExecStartPost')`).

Stock Hermes writes the gateway unit with three commands on the same launcher (`hermes_cli/gateway.py:3332, 3346, 3347` in both the pinned stock archive and the integration source):

```
ExecStart=<root>/.hermes/bin/hermes gateway run
ExecStop=-<root>/.hermes/bin/hermes --run-module gateway.systemd_stop_mark
ExecStopPost=-<root>/.hermes/bin/hermes --run-module gateway.cgroup_cleanup
```

CT 114 confirms the format on a real host: its gateway reports `ExecStop` and `ExecStopPost` on the same managed launcher as `ExecStart` (`ct114-systemctl-show.txt`). On CT 114 this is harmless, because the fragment names `/.lifeos-releases/` and preparation replaces it.

Scenario on development: the gateway unit runs `~/workspace/hermes-agent/.hermes/bin/hermes`, which is `installation_command`'s form for a stock-installed unit of that checkout, so it carries the same forwarder in `ExecStop` and `ExecStopPost`. The fragment does not name `/.lifeos-releases/`, so the gateway is not replaced. The refusal message tells the owner to "Point the unit at ~/.local/bin/hermes". The brief describes exactly that edit ("gateway and dashboard ExecStart are pointed at ~/.local/bin/hermes"). After that edit, preparation accepts (probe: `dev layout, ExecStart repointed, ExecStop/ExecStopPost still on checkout forwarder -> accepted`). After the transition, each gateway stop runs `systemd_stop_mark` and `cgroup_cleanup` from the managed 0.7.x runtime through the forwarder. If the managed runtime is removed later, both commands fail silently because of the `-` prefix. This is the R2-1 failure class for the stop path.

Assumption: I did not inspect the development host's unit. The conclusion holds if its gateway unit was written by `hermes gateway install` from the workspace checkout. Check with `systemctl --user show hermes-gateway -p ExecStop -p ExecStopPost` on development.

Fix: add `ExecStop`, `ExecStopPost`, `ExecReload`, and `ExecCondition` to `UNIT_COMMANDS`. On the known hosts this adds no refusal: CT 114 dashboard and Pulse have no stop commands, CT 114 gateway is replaced, `ExecReload=/bin/kill` is not a forwarder, and template units (`release_services.py:71`) write only `ExecStart`. Add a test for a stop command on the forwarder. The refusal message could say "Point every command of the unit at ~/.local/bin/hermes". The commit subject "check every command a Hermes unit runs" is not true until this is done.

### M2 (Low) No test covers ExecStartPost

Mutation `no ExecStartPost` passes all tests. `test_transition_checks_every_command_of_a_unit` covers multiple `ExecStart` and `ExecStartPre` only. One more `assertRaises` with `ExecStartPost` closes it, and the same test pattern fits M1.

### M3 (Info)

- Design section 10 step 4 says preparation reads "each gateway, dashboard, and Pulse command" and exempts "a gateway unit that preparation replaces". It does not say that a replaced gateway refuses a drop-in that sets a command. One sentence would match the code. The CHANGELOG line still matches.
- `docs/verification/2026-10-17-inplace-e2e/README.md` row 93 quotes the refusal text of that run up to "managed runtime.". The new message only adds text after that point, so the record stays correct.
- `_check_replaced_drop_ins` treats every `Exec*` key as a command, including the sandbox options `ExecSearchPath=` and `ExecPaths=`. No known host uses them. A pattern such as `^\s*Exec(Start|Stop|Reload|Condition)` would be exact; this is optional.
- `DropInPaths` is split on whitespace, so a drop-in path with a space would refuse as unreadable. No known host has one.
- Test lines reach 165 characters (`tests/test_inplace_services.py:121-122`, several in `tests/test_inplace_preparation.py`). The product file already has six lines over 120, so this is style only.

## Docs and standards

- ABOUTME headers are present in all four touched files and in the raw scripts.
- Names (`parse_show`, `_command_programs`, `_check_replaced_drop_ins`, `UNIT_COMMANDS`) are clear. Comments and docstrings describe behaviour, not history.
- The diff contains no em dashes or en dashes.
- The mock boundary (the service manager's text, parsed by the real `parse_show`) is now closer to the real interface than in round 2. File checks stay real.

## Review priorities for Adrian

1. M1: add the stop and reload commands to `UNIT_COMMANDS` with one test. First confirm the development gateway's `ExecStop` and `ExecStopPost` with the command above. This is one constant, one message, and one test.
2. M2: one assertion for `ExecStartPost`.
3. M3: one sentence in design section 10 step 4.

VERDICT: NOT CLEAN
