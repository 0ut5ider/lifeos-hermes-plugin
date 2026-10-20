# Review of 1c6b58f9 (keep a replaced dashboard's address)

- Date: 2026-10-18
- Role: code reviewer
- Model: Opus 5.5 (claude-opus-5-5)
- Question: Does commit 1c6b58f9 safely and completely carry a hand-started dashboard's `--host` and `--port` into the created `hermes-dashboard.service` unit (injection, parsing, plan binding, dropped options, tests)?

Raw data: `raw/` (test outputs, parser probe script and output, Hermes source excerpts, program journal check excerpt).

## Test runs

All five modules pass in the frozen environment:

| Module | Result |
|---|---|
| test_consumer_scan.py | 12 tests OK |
| test_inplace_services.py | 11 tests OK |
| test_release_configuration.py | 10 tests OK (includes systemd-analyze verify of the created unit) |
| test_inplace_plan.py | 14 tests OK |
| test_inplace_worker.py | 24 tests OK |

## Blocking

### B1. A hand-started `hermes serve --host 0.0.0.0` still loses its address

`consumer_scan._role` classifies a process as `dashboard` when its argv contains `dashboard` **or** `serve`, so a hand-started `serve` process is offered a dashboard unit and stopped by `replace_with_units`. `dashboard_options` only looks for the literal `dashboard` token and returns `{}` for `serve`.

Probe (`raw/probe-out.txt`):

```
['serve', '--host', '0.0.0.0', '--port', '9119'] dashboard -> {}
```

Scenario: an owner runs the documented remote backend `hermes serve --host 0.0.0.0 --port 9119` in tmux on a headless host, then runs `hermes lifeos-release prepare`. Preparation offers the dashboard unit, the worker stops `serve`, and the created unit listens on 127.0.0.1:9119. The remote desktop client loses its backend. This is the same failure the commit fixes for `dashboard`. A second effect: one `serve --host 0.0.0.0` plus one `dashboard --host 0.0.0.0` gives `{}` and `{'host': '0.0.0.0'}`, so preparation refuses with "different addresses" (fail closed, but wrong reason).

Fix: start option parsing after the first `dashboard` or `serve` token, matching `_role`, and add a `serve` case to `DashboardOptionTests`. Hermes's own named-profile re-exec (`main_dashboard.py`) passes `--host`/`--port` to both `serve` and `dashboard`, so the same two options apply.

## Non-blocking

1. **argparse prefix abbreviations.** The Hermes dashboard parser uses the argparse default `allow_abbrev=True`, so `hermes dashboard --ho 0.0.0.0` or `--hos=0.0.0.0` runs on 0.0.0.0. The scanner returns `{}` (probe line 3) and the unit binds 127.0.0.1. Rare. A cheap fail-closed guard: refuse any token after the command that is a strict prefix of `--host` or `--port` (length >= 3). Parsing with Hermes's own `build_dashboard_parser` via `parse_known_args` would be the most faithful alternative.
2. **Equivalent addresses refuse.** `{}` and `{'host': '127.0.0.1'}` (or `{'port': 9119}`) are the same effective address, but the set comparison treats them as different. Fail closed; normalizing to the Hermes defaults (127.0.0.1, 9119) before comparison would avoid a confusing refusal.
3. **Stale ABOUTME.** `consumer_scan.py` line 2 still says "Reports process IDs and command names only; it never exports arguments or environment values." The module now exports `--host` and `--port`. Update the header.
4. **Review UI.** `dashboard_options` is not shown to the owner. It is bound to the approval: `inspect_inplace` recomputes it live, `service_files` writes it into `generated/hermes-dashboard.service`, and `ProgramTransaction.check_prepared` compares that source's fingerprint to the reviewed `after` identity, whose digest is sealed in plan.json (`program_entries_sha256`). A changed address between review and apply therefore refuses. Because the value only preserves what the owner already runs, hiding it is acceptable. Showing "the created dashboard unit listens on 0.0.0.0:9119" would still help, because a public bind is security-relevant and the docstring calls the value "reviewed".
5. **Port 0 refuses.** Hermes accepts `--port 0` (auto-assign). Refusing is the right choice for a unit; the message tells the owner what to do.
6. **Unicode digits.** `'９１１９'.isdecimal()` is true and `int()` gives 9119, the same as argparse `type=int`. The unit gets ASCII `9119`. Consistent.

## Checks that came out clean

### 1. Injection and quoting

- `DASHBOARD_HOST` allows only `[A-Za-z0-9._:\[\]-]{1,253}`. It excludes `$`, `%`, quotes, backslash, whitespace, `;`, and control characters. Port becomes an `int`. Probe: `%h`, empty `--host=`, `$(id)`, `a b` all refuse.
- `_quoted(..., command=True)` then wraps each word in double quotes and escapes `\`, `"`, `%`, `$`. Even without the regex, a host could not add a systemd directive or specifier. The new test runs `systemd-analyze --user verify` on the created unit.
- `-x` passes the regex, but argparse in a running Hermes rejects `--host -x`, so no live process can carry it.
- IPv6: `::` and `[::1]` pass and are copied verbatim, so the unit binds exactly what the running process bound. Hermes treats `::` as a wildcard bind (`web_server.py` line 621) and `::1` as loopback. `[::1]` is not in `_LOOPBACK_HOST_VALUES`; whatever behaviour it had in the hand-started process, the unit reproduces it. Consistent.

### 2. Parsing

- First `dashboard` token: options before it (top-level) are ignored. The test covers `--host 0.0.0.0 dashboard` giving `{}`. The named-profile re-exec form `-p default dashboard --port 9119 --host 0.0.0.0 --open-profile work` parses correctly (probe line 2).
- `--host=`/`--port=` forms work. A missing value after `--host` refuses. Repeated options: last wins (probe line 4), the same as argparse.
- The stock launcher's `-c <code>` is a single argv word, so `'dashboard' in words` never matches inside the code.
- Non-UTF-8 bytes decode to U+FFFD and the regex refuses them.

### 3. Plan flow

- In-place `selected` comes from `inspect_inplace`, run live in `_review_operation` and in `inplace_worker._run`. It is not read from plan.json, so plan.json needs no new key, and `validate_plan` only checks the plan's SHA-256.
- Binding, as in non-blocking item 4: the unit bytes reach the program journal, `check_prepared` compares the regenerated source with the reviewed identity, and the worker calls `program_plan` before `replace_with_units` stops anything.
- Recovery paths (`recover`, `restore`, and fresh forward recovery) do not regenerate the unit, so a stopped dashboard (`{}`) cannot change the recovered plan.

### 4. Dropped options

- `--insecure` is a documented no-op in this Hermes. Dropping it is harmless.
- `--skip-build`: the unit without it builds the web UI only when the build is stale (`_do_build_web_ui`). If build tools are missing and the dist is stale, the unit start fails. The worker's start verification should then catch the failure (I did not trace that path in this review). This is the same command the project's standard unit already uses, so I accept it.
- `--isolated` and `--no-open` are always added. `--open-profile` (internal) and `--tui` (ignored) do not matter.
- Profile: the unit pins `HERMES_HOME` to the selected profile. Replacing a non-isolated named-profile dashboard, which Hermes re-execs to the machine root, with an isolated profile unit was decided in a43ee9ae, not in this commit.

### 5. Tests

The tests cover the main forms (space and `=`, IPv6 `::1`, options before the command, refusals), the inventory carry-through, the different-address refusal, and the created unit text plus `systemd-analyze verify`. Gaps: no `serve` case (B1), no abbreviation case, and no end-to-end test that `release_worker.program_plan` passes `dashboard_options` into the unit. That last link is one line and is easy to read.

### Standards

No em dashes in the diff. Names are clear. No history in code comments. The CHANGELOG entry is appropriate. ABOUTME staleness is in non-blocking item 3.

VERDICT: NOT CLEAN
