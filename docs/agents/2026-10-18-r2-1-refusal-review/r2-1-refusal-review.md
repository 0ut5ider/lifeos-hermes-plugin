# R2-1 refusal review

- Date: 2026-10-18
- Role: code reviewer
- Model: Claude Opus 5.5 (claude-opus-5-5)
- Question: Is `git diff 48bbd0e6..36615439` on `feature/minimal-install-review` correct? It replaces the transition's repointing of service launchers outside `~/.local/bin` with a preparation refusal (`check_service_launchers`). The review covers ExecStart parsing against real systemd semantics, leftover readers of `transition_launchers`, the tests, the docs, and the coding standards.

Raw data in `raw/`: the reviewed diff, the probe script and its output, both test runs, and the mutation run.

## Summary

The removal is complete and clean. Nothing in product code or tests reads `transition_launchers` or `managed_service_launchers` any more. Both test modules pass (21 and 14 tests). The docs match the code, and the diff adds no em dashes. The weak part is `check_service_launchers` itself. It parses unit files by hand and fails open, so several unit layouts that systemd 259 (the Fedora 44 version) accepts pass preparation while the unit still runs a managed forwarder. No test checks that preparation calls the new check.

## Findings

### F1 (Medium) The check fails open on a line continuation or an unparseable ExecStart

`optional/lifeos_release_manager/inplace_preparation.py:83-87`. `_service_value` reads one physical line, so `ExecStart=/path/hermes \` yields a value that ends in a backslash. `shlex.split` raises `ValueError` ("No escaped character") on it. The `except` sets `executable = None`, and the loop `continue`s. An unterminated quote takes the same path.

Scenario: the owner's dashboard unit on development reads

```
ExecStart=/home/u/workspace/hermes-agent/.hermes/bin/hermes \
    dashboard --isolated --no-open
```

systemd runs the workspace forwarder, which forwards to the managed runtime. Preparation accepts it (probe: `line continuation ... accepted`). After the transition the dashboard still runs the managed release. It breaks when the owner approves removal of the retained job directories, or when the workspace checkout rewrites the forwarder. This is exactly the R2-1 failure. A refusal check that fails open on input it cannot parse defeats its purpose. It should join continuation lines, and refuse (or at least not accept) when it cannot determine the executable.

### F2 (Medium) Hand parsing differs from systemd's effective ExecStart in several accepted layouts

`optional/lifeos_release_manager/inplace_preparation.py:50-66, 81-90`. The probe (`raw/probe-output.txt`) shows that preparation accepts each of these. Each one runs the workspace forwarder under systemd:

| Layout | Why it is missed |
|---|---|
| `ExecStart = /path ...` (spaces around `=`) | `startswith('ExecStart=')` does not match. `systemd-analyze --user verify` accepts the form. |
| `ExecStart=%h/workspace/hermes-agent/.hermes/bin/hermes ...` | The `%h` specifier is not expanded, so `Path('%h/...').is_file()` is false. |
| Drop-in in `hermes-.service.d/` | systemd.unit(5) documents dash-truncated drop-in directories. `hermes-.service.d/` applies to both `hermes-gateway.service` and `hermes-dashboard.service`. `_unit_texts` reads only `<name>.d/`. |
| Drop-in in `service.d/` (applies to all services) | The same reason. |
| `ExecStart=\|/path ...` | systemd 259 documents the `\|` prefix (run through the shell). `lstrip('-@+!:')` does not remove it. |
| Unit or drop-in under `/etc/systemd/user`, `~/.local/share/systemd/user`, or `user.control` | `_unit_texts` reads only `~/.config/systemd/user`. |
| `ExecStart=/bin/sh -c "exec ~/workspace/.../hermes dashboard"` | The check inspects only the first word. |

The codebase already reads the effective command from the manager. `release_plan.py:72-81`, `release_services.py:153`, and `release_services.py:168-179` parse `path=` from `systemctl --user show -p ExecStart`. Using that source here removes the specifier, whitespace, continuation, drop-in search path, and prefix problems at the same time. Gateway and dashboard units on a managed host were admitted through `release_plan.py:72-81`, which requires a fixed home-relative `path=`. That limits the realistic cases to owner edits after installation, so I rate this Medium, not High. The `_unit_texts` limits also apply to the existing checks in `transition_gateway_unit`, so part of this predates the diff.

### F3 (Low) Any file in `~/.local/bin` is exempt, but the transition repoints only three names

`optional/lifeos_release_manager/inplace_preparation.py:88`. The exemption is `executable.parent == account`. `transition_launchers` (`inplace_plan.py:186-197`) replaces only `hermes`, `hermes-agent`, and `hermes-acp`. `release_plan.py:72-81` recorded whatever home-relative launcher the gateway or dashboard unit ran, so the managed release could have rewritten for example `~/.local/bin/hermes-dev`. Scenario: a unit runs `~/.local/bin/hermes-dev`, a managed forwarder. Preparation accepts it (probe: `other forwarder in ~/.local/bin ... accepted`), and the transition leaves it on the managed runtime. The old code had the same exemption, so this predates the diff. The fix is small: compare against the three published targets, not the directory. The docs say "outside `~/.local/bin`", so they would need the same change.

### F4 (Low) No test checks that preparation calls the new check

`optional/lifeos_release_manager/inplace_preparation.py:108`, `tests/test_inplace_preparation.py:265-304`. The new tests call `check_service_launchers` directly on real files, so they are not mock-only. But nothing goes through `transition_gateway_unit` or `prepare_inplace` with a forwarder unit. Mutation: I replaced line 108 with `pass` in an extracted copy. All 21 tests in `test_inplace_preparation.py` still pass (`raw/mutant-tests.txt`). Someone could delete or move the call without a test failing. Add one `transition_gateway_unit` case with a dashboard unit that runs a workspace forwarder.

### F5 (Low) The verification record does not contain the CT 114 refusal evidence

`docs/verification/2026-10-17-inplace-e2e/README.md:87` still says "The layout of defect 9 is not rehearsed on a container." The caller reports CT 114 evidence: preparation refused a dashboard unit on a workspace forwarder, and after the owner repointed the unit, the transition applied and the restore rolled back. The diff does not record that run or its raw output. If this evidence is the release gate for R2-1, add it to the record and correct line 87.

### F6 (Info) Smaller semantic gaps

- False refusal: a forwarder outside `~/.local/bin` that is a symlink to `~/.local/bin/hermes` is refused (probe: `symlink elsewhere to account launcher`). The transition repoints its target, so the unit would be correct afterwards. This is unlikely and harmless, because the owner can repoint the unit.
- False refusal: a drop-in that has only `ExecStart=` makes systemd refuse to load the unit, but the check falls back to the main file's command and refuses. This is harmless.
- `inplace_preparation.py:87-89`: a bare file name (`ExecStart=hermes`) resolves against the preparation process's working directory. systemd uses its fixed search path instead. The effect is negligible.
- `inplace_preparation.py:89`: `read_text` on an unreadable file raises `PermissionError`, which is a traceback and not a `ReleaseRejected`.
- `inplace_preparation.py:90-91`: for `com.lifeos.pulse.service`, the message says "Point the unit at ~/.local/bin/hermes". Pulse runs `~/.local/bin/bun`. That is a nit.
- Behaviour change to note for Adrian: a launcher that the managed `plan.json` lists outside `~/.local/bin`, and that none of the three units runs, is now neither repointed nor refused. An example is a workspace forwarder that is on the interactive `PATH`. Interactive use of it stays on the managed runtime until the job directories are removed. This matches the owner decision as worded ("refuse units"), but the old code covered it.

## Checks that pass

1. Removed code: `git grep` over the repository, excluding `docs/agents` and `docs/verification`, finds no `transition_launchers` request key, no `managed_service_launchers`, and no `services=` argument. `transition_launchers` is called only at `inplace_plan.py:148`. `running_source` and `parse_json` are still imported where they are used. The import of `running_source` was removed from `inplace_preparation.py`, and nothing else there used it. No request validator lists the removed key.
2. Ordering: `check_service_launchers` runs after the `MANAGED_RUNTIME` text loop in `transition_gateway_unit`. This makes the `MANAGED_RUNTIME in str(executable)` skip safe: that loop already refused direct managed runtime commands in drop-ins and non-gateway units.
3. Prefixes `-`, `@`, `+`, `!`, `!!`, and `:` are stripped correctly, and quoted commands like the ones stock Hermes writes (`_systemd_command`) parse correctly (probe: `quoted like stock Hermes ... REFUSED`). Missing executables pass, which is correct. The last drop-in assignment wins, and the test covers a reset with the `-` prefix.
4. Tests: `test_inplace_preparation.py` ran 21 tests, OK. `test_inplace_plan.py` ran 14 tests, OK. The tests use real temporary files, not mocks.
5. Docs: design section 10 step 4, the section 15 table row B1, the CHANGELOG line, and verification README item 9 match the code ("outside `~/.local/bin`", the gateway, dashboard, and Pulse units, and the advice to point the unit at `~/.local/bin/hermes`). The added lines contain no em dashes or en dashes.
6. Standards: the ABOUTME headers are present in all touched code files. The new docstrings and comments do not describe history. In the test comment "gets the stock unit instead", "instead" contrasts two behaviours and does not describe history. The names are clear (`SERVICE_UNITS`, `check_service_launchers`).

## Review priorities for Adrian

1. F1 and F2 together: decide whether the check should read `systemctl --user show -p ExecStart` (one source of truth, already used elsewhere) or keep file parsing and close the gaps. In both cases, unparseable input should refuse and not pass.
2. F4: add the wiring test.
3. F5: record the CT 114 evidence.

VERDICT: NOT CLEAN
