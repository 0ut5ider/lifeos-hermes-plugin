# rc2 fixes review

- Date: 2026-10-18
- Role: code reviewer
- Model: Opus 5.5 (claude-opus-5-5)
- Question: Review `git diff 7c22a47c..ac78261a` (a43ee9ae, 22905874, 7b677188, d2dc696e, ac78261a) on branch
  `feature/minimal-install-review`, the fixes from the 0.8.0-rc.1 live test. Focus on consumer detection, Bun lookup,
  the claim message, the security-sensitive dashboard login resolution for removal recovery, and the docs.

Raw data is in `raw/`: test outputs (`rv2-test_*.txt`), two probe scripts with their output, and a real
`systemctl --user show` sample from a transient unit (systemd 259, Fedora 44).

## Tests

All six requested modules pass in the frozen environment:
test_consumer_scan (10), test_bun_program (4), test_portability_dashboard (5), test_removal_recovery (10),
test_inplace_services (9), test_inplace_preparation (29). No warnings in the captured tails.

## Blocking findings

### B1. A password hash in the unit's `Environment=` never authenticates (d2dc696e)

`dashboard_unit_environment` parses `Environment=` with `shlex.split`. systemd prints each `$` in a value as `\$`
inside a double-quoted entry. POSIX `shlex` keeps the backslash before `$` inside double quotes. Every scrypt hash
contains `$`, so the parsed hash becomes `scrypt\$16384\$8\$1\$...`, `_verify_password` sees scheme `scrypt\`, and
login fails.

Measured (`raw/unit_hash_probe.py`, real transient unit, real `inplace_services.show`):

```
parsed: [..., 'HERMES_DASHBOARD_BASIC_AUTH_PASSWORD_HASH=scrypt\\$16384\\$8\\$1\\$pF8I...']
hash equal: False
authenticate refused: InvalidCredentialsError invalid username or password
```

Failure scenario: the owner sets `HERMES_DASHBOARD_BASIC_AUTH_USERNAME` and `..._PASSWORD_HASH` inline in
`hermes-dashboard.service`, which is the case the commit adds. Preparation checks only the username, so it passes and
removal applies. The standalone recovery CLI then refuses the correct dashboard password, so recovery and rollback
are unavailable. A plaintext password with `$` or a backtick fails the same way. The test
`test_inline_unit_environment_supplies_the_login` passes a pre-split list and never exercises the parser.
Fix direction: decode systemd's quoting (systemd escapes `"`, `\`, `$`, and a backtick), or read the values without
the quoting, and add a test that parses captured real `systemctl show` output (see `raw/systemctl-show-sample.txt`).

### B2. An optional or non-private `EnvironmentFile` makes removal impossible (d2dc696e)

`_unit_login` reads every `EnvironmentFiles` entry through `_private_bytes`. The `(ignore_errors=yes)` flag is
dropped, so a missing optional file gives `fingerprint(...) is None` and raises
"Standalone recovery requires the private current dashboard configuration". A root-owned or 0644 file such as an
`/etc/default/...` file, or a path below a symlinked directory (`fingerprint` refuses a non-physical parent), also
refuses, even when the file holds no login variable.

Failure scenario: the unit has `EnvironmentFile=-%h/.hermes/.op.env` (Hermes's own env loader comment describes this
pattern) and the file does not exist. In rc.1, removal worked from `config.yaml`. Now removal preparation always
refuses. This is a regression of the same kind that the commit fixes. Fix direction: skip a missing file when
`ignore_errors=yes`, and apply the private-file rule only when the file supplies a login variable (or refuse with a
message that names the file).

### B3. A blank `.env` value does not shadow the unit value as it does in Hermes (d2dc696e; low likelihood)

Hermes loads the profile `.env` with `override=True` and writes `''` for `KEY=`. That blank value replaces the unit
value, and `resolve_env_or_cfg` then falls back to `config.yaml`. `basic_settings` skips a blank layer and takes the
unit value. Measured (`raw/blank_env_probe.py`, Hermes's real `load_hermes_dotenv`):

```
LifeOS accepts unit-password: True
LifeOS accepts config-password: False
Hermes env value after .env load: ''
```

Failure scenario: `.env` has `HERMES_DASHBOARD_BASIC_AUTH_PASSWORD=` and the unit sets a plaintext password. The
dashboard accepts the `config.yaml` password. Recovery accepts only the unit password and refuses the password the
owner uses every day. The configuration is unusual, but the commit claims parity in a security decision. Fix
direction: within the environment layers, the first layer that defines the key wins even when blank. Only the final
environment-versus-config choice treats blank as unset. Add the test.

## Non-blocking findings

1. Parity gaps that the commit does not claim but that change the resolved login. In each case the result fails
   closed or uses another owner-private value. None gives a same-account attacker anything new, because that account
   can already rewrite the private `config.yaml`.
   - The Hermes managed scope `/etc/hermes/.env` (or `$HERMES_MANAGED_DIR`) loads last with override. The managed
     `config.yaml` also merges into `load_config`.
   - External secret sources (the `secrets:` block, Bitwarden) inject env values after `.env`.
   - `config.yaml` values go through `${VAR}` / `${env:VAR}` expansion in Hermes. LifeOS hashes a config
     `password: ${env:X}` literally, so recovery accepts the literal text `${env:X}`. `password` in config is newly
     accepted by this commit, so this is new. The literal is in the owner-private file, so the risk is low. Refusing
     a value that contains `${` is the simple fix.
   - The user manager environment (`environment.d`, `systemctl --user set-environment`) and a hand-started
     dashboard's shell exports are not read. With a43ee9ae, a hand-started dashboard is now a supported operator, and
     its login can come from its shell.
   - Hermes parses `.env` as `utf-8-sig` with a latin-1 fallback. LifeOS uses strict UTF-8, so a BOM hides the first
     key and invalid UTF-8 raises `UnicodeDecodeError` (a `ValueError`, so the callers still refuse).
   - Hermes applies `str(...)` to non-string config values (for example, a numeric YAML password). LifeOS treats
     them as unset. This fails closed.
2. A non-private profile `.env` (for example, 0644 and written by hand) now refuses removal even when it has no login
   key. In rc.1, removal worked. Hermes writes `.env` as 0600 and `hermes doctor` repairs the mode, so this is less
   likely than B2. The refusal message names "dashboard configuration", not `.env`.
3. In `_private_bytes`, the second `fingerprint` call can raise `ProgramConflict` (not caught there). It is a
   `ValueError`, like `ReleaseRejected`, so the callers still refuse. `fingerprint` hashes the whole file before the
   1 MiB size check, so the size limit does not bound the read. This is the same as before the commit.
4. The recovery CLI can run without a user bus (an SSH session without `XDG_RUNTIME_DIR`). Then `show` fails, the
   unit layer is silently empty, and a unit-supplied login refuses with the generic recovery message. A message that
   says the service manager is unavailable would help the owner.
5. `dashboard_unit_environment` has no test against real output (multiple `EnvironmentFiles` lines,
   `ignore_errors=yes`, quoted values). `parse_show` joins repeated lines correctly. I confirmed this on systemd 259.
6. a43ee9ae: the quote terminator is correct for the stock launcher. `_inline_string_literal` is `repr()` on POSIX,
   so the root is always followed by `'` or `"`, and the sibling test covers `hermes-agent-other`. Other terminators
   (`)`, `,`, `;`, a newline) cannot directly follow a path in Python code. In shell `-c` code, `cd /path;x` is still
   missed, but the cwd evidence usually covers that case. The launcher embeds `Path(repo_root).resolve()`. The scan
   compares `Path(...).absolute()`, so a symlinked checkout or home (for example, Fedora Atomic `/home` ->
   `/var/home`) would not match. This is the same as before the commit, and it also affects the exe and cwd
   evidence.
7. Operators with a43ee9ae: the hand-started dashboard that serves the request has role `dashboard`, so the
   `operators` exclusion (role `other` only) does not apply. When no dashboard unit is loaded, the dashboard is
   offered a unit, and the apply terminates it after the start-time check. The apply worker is independent of it:
   `cli.launch_worker` uses `systemd-run --user` whenever `plan.json` `services` is set. The in-place plan always
   sets `services` to a non-empty dict. The preparation worker is a child of the dashboard, but it finishes before
   the apply. If a dashboard unit is loaded and the serving dashboard is also hand-started, preparation blocks and
   names the serving dashboard. That is correct, but the owner may find it confusing. The dashboard is now detected,
   so interactive CLI sessions (role `other`, not an ancestor) block as designed.
8. 22905874: correct. The order is PATH, then the account database home `~/.local/bin/bun` (executable regular
   file), then bare `bun`. The tests cover all three cases, and one test confirms that `HOME` is ignored.
   `selection_worker.py:132` still falls back to `~/.bun/bin/bun`, and `update_worker.py` uses `$HOME`. Those are
   inconsistent but outside this diff.
9. 7b677188: works and is tested. "before memory workflows" reads awkwardly. "before you use memory workflows" is
   clearer. A dangling `lifeos-memory.json` symlink gets the generic message, which is acceptable.
10. ac78261a: no em dashes in the diff. `ProviderNotConfiguredError` exists in Hermes
    (`agent/auxiliary_unavailable.py`), and "Recover memory workflow" matches the UI label. The reinstall proposal is
    clearly marked as not implemented.
11. Standards: ABOUTME headers are present in all touched and new files, and the names are fine. The code comment
    "systemd applies environment files after Environment= assignments." is correct and is not a history comment.

## Removal preparation caller (removal_preparation.py:136)

The caller compares only `settings['username']` with the owner. A wrong password hash (B1, B3) therefore passes
preparation and fails only at recovery, after removal has applied. A cheap guard is to also require that the
resolved hash parses as `scrypt$n$r$p$salt$dk`. That would have caught B1 before any change.

VERDICT: NOT CLEAN
