# Review round 2: 1c6b58f9 + 11e98e5d (keep a replaced dashboard's address)

- Date: 2026-10-18
- Role: code reviewer
- Model: Opus 5.5 (claude-opus-5-5)
- Question: Does 11e98e5d close the round 1 blocking finding (hand-started `serve` loses its address), and are its abbreviation guard, default-dropping, and tests correct against the real Hermes `dashboard`/`serve` parsers?

Raw data: `raw-round2/` (probe script and output, three test outputs).

## Test runs

| Module | Result |
|---|---|
| test_consumer_scan.py | 12 tests OK |
| test_inplace_services.py | 11 tests OK |
| test_release_configuration.py | 10 tests OK |

## B1 (round 1): closed

`dashboard_options` now starts after the first `dashboard` or `serve` word, matching `_role`. Probe: `-p default serve --port 9119 --host 0.0.0.0 --open-profile work --ssh-owner-nonce n1` gives `{'host': '0.0.0.0'}`. A new test covers `serve --host 0.0.0.0 --port 9200`.

## Abbreviation guard

Real options (`hermes_cli/subcommands/dashboard.py`, `_add_server_runtime_args` plus per-parser extras), all with argparse default `allow_abbrev=True` and `add_help=True`:

- both: `-h/--help`, `--port` (int, default 9119), `--host` (default "127.0.0.1"), `--insecure`, `--skip-build`, `--isolated`, `--open-profile` (suppressed), `--stop`, `--status`
- dashboard only: `--no-open`, `--tui` (suppressed), nested `register` subcommand
- serve only: `--no-open` (suppressed), `--ssh-session-token-file PATH`, `--ssh-owner-nonce NONCE`

No real option other than `--host`/`--help` starts with `--h`, and only `--port` starts with `--p`. There is no `--profile` on either subparser. So:

- `--p`, `--po`, `--por`: argparse accepts them as `--port`; the guard refuses (probe). Correct fail-closed.
- `--ho`, `--hos`: argparse accepts as `--host`; the guard refuses. Correct.
- `--h`: argparse rejects it as ambiguous (`--help`, `--host`), so no live process carries it; the guard refuses, which is harmless.
- `-h`, `--help`, `--s`, `--i`, `--o`, `--ssh`, and every full option name pass through as `{}` (probe). No false refusal on any real option or abbreviation of another option.
- The guard also scans value words. A value starting with `--h`/`--p` (for example a nonce) would refuse, but argparse already rejects a separate value word that starts with `--`, and the `=` form splits on the option name. No live process can trigger this.
- `--` and `-p` are length 2 and skipped. `dashboard -- --port` refuses, but argparse rejects that command line anyway.

## Default-dropping

Hermes defaults are exactly `--port default=9119` and `--host default="127.0.0.1"` (dashboard.py lines 18-19), and `start_server(host="127.0.0.1", port=9119)` (web_server.py line 1591). The filter compares the port after the `int()` conversion, so `--port 9119` and `--port=9119` drop. This also fixes round 1 note 2 and matters in practice: the named-profile re-exec (`main_dashboard.py` line 979) always writes `--port <n> --host <h>` explicitly, so a re-exec'd default dashboard now matches a bare one instead of refusing as "different addresses". `localhost` is kept verbatim (not normalized), which only reproduces what the process ran with.

`release_services.service_files` adds only the keys present, so a single non-default value (for example `{'host': '0.0.0.0'}`) gives `--host 0.0.0.0` with the default port. Correct.

## Tests

The tests cover `serve`, the explicit-default case, `--ho`, and `serve --por=9200`. The ABOUTME header is updated (round 1 note 3). Not covered by a test, but verified by the probe: `--p` (the shortest abbreviation argparse accepts) and the re-exec argv form.

## Non-blocking

1. A hand-started `serve` is replaced by a unit that runs `dashboard`, not `serve`. `serve` skips the web UI build (`headless_backend=True`), but the unit does not. On a headless host without npm and with a stale dist, the unit start could fail where `serve` ran. The role mapping predates these commits, and round 1 accepted the same build behaviour for `dashboard`. I did not trace whether the worker's start check catches the failure and restores.
2. Round 1 note 4 (the review UI does not show a public bind) is still open. It is acceptable as before.

VERDICT: CLEAN
