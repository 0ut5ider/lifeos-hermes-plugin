# In-place fixes review

- Date: 2026-10-17
- Role: independent reviewer (read-only; no tracked file changed, nothing committed)
- Question: are the eight commits `b19e793e..56218073` on `feature/minimal-install-review` correct and safe, and what cases do they miss? Focus areas 1 to 5 from the brief.
- Model: Claude Fable 5.1

Raw data in this directory: `review-diff.patch` (code and test diff of the range), `focused-tests.txt` (four focused test files, all pass), `systemd-needdaemonreload-experiment.txt`, `killmode-digest-check.txt`.

## Summary

Two should-fix findings, both in the transition path and both untested by the container runs (the crash matrix ran on host 112, a non-transition host; host 114 had a gateway unit in stock format). Each one leaves the host in `recovery_required` with a recovery that refuses the same way, so the owner must intervene by hand. Everything else I checked holds up; the receipt, `.env`, probe, and failure-record changes have no problem I could find.

## Findings

### 1. should-fix: a crash or failure between unit publication and `daemon-reload` makes recovery and rollback refuse

Files: `optional/lifeos_release_manager/inplace_worker.py` lines 221 to 222 (`_rollback`: `adopt_units`, `_quiesce` before `programs.restore()`), 285 to 286 (recover branch: `adopt_units`, `_quiesce`), 326 to 330 (publish, `checkpoint('programs-published')`, `clear_bytecode`, `daemon-reload`, `adopt_units`). `lifeos_hook_bridge/profile_services.py` line 170 (`NeedDaemonReload != 'no'` refusal).

Scenario: transition host. `programs.apply()` replaces `~/.config/systemd/user/hermes-gateway.service`. The worker dies at `checkpoint('programs-published')` (the crash-matrix checkpoint) or `clear_bytecode` raises, before line 329 runs `daemon-reload`. The gateway unit is enabled, so systemd keeps it loaded and reports `NeedDaemonReload=yes` (verified, see `systemd-needdaemonreload-experiment.txt`). Then:

- In-process failure: `_rollback` calls `adopt_units` first. `_inspect_definition` raises `MemoryUnavailable('The profile service has unreviewed program or process properties')`. The rollback aborts before `programs.restore()`. The release worker marks `recovery_required`.
- Recovery: `_run(action='recover')` calls `adopt_units` at line 285 before anything else and raises the same way. Every retry refuses. Without `adopt_units`, `_quiesce` at line 286 would refuse identically, so the pre-existing controller rule is what bites; the new commits made it reachable by putting a unit file into the program transaction.

Owner workaround: run `systemctl --user daemon-reload` by hand, then recover.

Fix: run `_systemctl('daemon-reload')` before the first `adopt_units` in `_rollback` (line 221) and before `adopt_units` in the recover branch (line 285). The call is idempotent and cheap. Add a crash-matrix run on a transition host at `programs-published`.

### 2. should-fix: a gateway unit created from the LifeOS template cannot be adopted (KillMode differs), and the host gets stuck

Files: `optional/lifeos_release_manager/inplace_preparation.py` lines 48 to 73 (`transition_gateway_unit`), `lifeos_hook_bridge/profile_services.py` lines 299 to 303 (substitution check), `optional/lifeos_release_manager/release_services.py` line 66 (`KillMode=control-group` in the template; identical in the 0.7.3 package), `hermes_cli/gateway.py` `generate_systemd_unit` (`KillMode=mixed`), `optional/lifeos_release_manager/release_worker.py` line 235 (a fresh managed install creates `gateway`, `dashboard`, `pulse` from the template when the units do not exist).

Scenario: an owner installed a managed release on a host without a gateway unit. The managed install wrote the template unit (`KillMode=control-group`, `ExecStart=~/.local/bin/hermes gateway run ...`). The transition generates the stock unit (`KillMode=mixed`). `KillMode` is part of the journaled definition (`PROPERTIES` minus the excluded keys), so after publication and reload `adopt_definition` finds the fragment hash in `allowed` but `recorded not in earlier` and raises `not a reviewed replacement` (`killmode-digest-check.txt`). Then the chain from finding 1 repeats: `_rollback` -> `adopt_units` refuses -> rollback aborts before `programs.restore()` -> `recovery_required` -> `recover` -> `adopt_units` refuses. Permanent until the owner restores the unit file by hand.

Note that for this class of unit the replacement is unnecessary: the template unit runs `~/.local/bin/hermes`, which `transition_launchers` already repoints to the stock checkout.

Fix (any one prevents the stuck state; I would do the first two):

- In `transition_gateway_unit`, replace the unit only when the existing file literally references `/.lifeos-releases/`, the same test the function already applies to the dashboard and Pulse units. Otherwise return `{}`.
- At preparation, parse `KillMode=` (and `WorkingDirectory=`) from the existing and generated texts and refuse the transition when they differ, so the refusal happens before publication, not after.
- Alternatively make the substitution in `adopt_definition` tolerate `KillMode` within the admitted set `{'mixed', 'control-group'}`; `_inspect_definition` already restricts it.

Also worth noting for 1 and 2 together: an `adopt_units` refusal inside `_rollback` is fatal to the rollback because `_quiesce`, `verify_stopped`, and `resume` all go through `_check_definition`. Preventing the refusal is the right fix; there is no cheap way to make `_rollback` survive it.

### 3. should-fix (low): a symlinked gateway unit silently keeps the managed definition

File: `inplace_preparation.py` line 60. `if not existing.is_file() or existing.is_symlink(): return {}` treats a symlinked unit like "no unit". The transition then proceeds with the managed gateway unit in place; `check_receipt` refuses after the restart (`another Hermes checkout`) and the operation rolls back. Correct outcome, wasted apply and rollback, misleading message. Fix: refuse at preparation when the unit is a symlink, with a message that names the file.

### 4. minor: the managed-runtime check reads only two fragments, not drop-ins

File: `inplace_preparation.py` lines 55 to 58. `hermes-dashboard.service.d/*.conf`, `com.lifeos.pulse.service.d/*.conf`, and the gateway's own drop-ins are not read. A drop-in with `Environment="PATH=.../.lifeos-releases/..."` survives the transition. `check_receipt` only catches it when the import path changes. The owner-created drop-in case is rare; adding `*.service.d/*.conf` to the scan is a few lines.

### 5. minor: `transition_gateway_unit` drops the generator's stderr

File: `inplace_preparation.py` lines 69 to 70. Same class as e2e defect 5. Record a stderr tail into the job (as `record_probe_output` does) before raising.

### 6. minor: 90 s `systemctl` timeouts next to the 300 s controller

File: `inplace_worker.py` lines 27 to 30 and 93 to 97. `_stop_created` runs `disable --now` with `timeout=90` and does not catch `TimeoutExpired`, which would abort `_rollback`. Created units use the template's `TimeoutStopSec=45s`, so 90 s is enough today. `lifeos_hook_bridge/update_worker.py` line 97 still stops the gateway with 45 s, out of this range but the same class as defect 1.

## Checked and found no problem

### Focus 1: `adopt_definition` and `adopt_units` paths (after `daemon-reload`)

- Substitution check: it proves the current definition equals the journaled one except the fragment hash, and both hashes are in `allowed`. An attacker who can write the unit file needs a reviewed hash to be adopted. `allowed` includes `before`, so adopting back is permitted while stopped; that is required by rollback. `_empty` runs before the rebinding, and the state must be `stopped`.
- Apply: drain under `before`, publish, reload, adopt `after`, resume with the journal matching. Correct.
- Failure after adoption: `_rollback` adopt (no-op), quiesce, restore programs, reload, adopt `before`, resume. Correct.
- Restore of an applied transition: journal `active` with `after`; the first `adopt_units` returns `False` before the state check (digest equal), quiesce, restore, reload, adopt `before` in state `stopped`, resume. Correct.
- Crash after reload, before adoption: journal `stopped` with `before`, disk `after`; recover adopts `after`, then rolls back. Correct.
- Crash in rollback after `programs.restore()` and after reload: journal `after`, disk `before`, state `stopped`; recover adopts `before`. Correct. Before the reload, see finding 1.
- Journal state `stopping` or `starting` with a differing digest cannot arise, because publication and restore happen only between a completed drain and resume.
- `adopt_units` skips when `services is None`, when the journal is absent (`state == 'none'`), and for roles not bound. The hashes come from `request.json` and are 64-hex, so the `ValueError` guard never fires in practice.

### Focus 2: `transition_gateway_unit`

- Determinism between preparation and apply is not needed: the unit is generated once, hashed into `request.json`, and `transition_unit_files` re-hashes `job/transition-gateway.service` against `after` at apply time (`inplace_plan.py` line 170). Good.
- Environment: `LD_LIBRARY_PATH`, `PYTHONPATH`, `PYTHONHOME`, `VIRTUAL_ENV` removed; `HOME` and `HERMES_HOME` set; `-I` and `cwd=profile`. `generate_systemd_unit` reads `get_hermes_home()`, the stock `PROJECT_ROOT` (imported from `source`), the installed unit for a fallback `LD_LIBRARY_PATH`, and existing `~/.local/bin`-style directories. The `.lifeos-releases` refusal on the output covers the leak that matters. Stock Hermes regenerates and compares the unit on every gateway start; because the same function with the same inputs produced the published file, the comparison matches (host 114 confirms).
- Gateway drop-ins: `DropInPaths` is excluded from the definition keys, but the drop-in files are included in `files`; they do not change across the transition, so adoption works with an owner drop-in. Working directory: template and stock both use the profile, so that key matches. Only `KillMode` differs (finding 2).

### Focus 3: receipt source

- `hermes_source()` resolves `hermes_cli.__file__` and takes `parents[1]`; `check_receipt` resolves `request['host']['source']`. Symlinked checkouts resolve on both sides. The profile location does not enter. `runtime_command` inserts the resolved checkout root at `sys.path[0]`, so a site-packages copy of `hermes_cli` cannot win. No legitimate host fails this.
- A receipt without `source` (older bridge) passes `read_receipt` and is refused by `check_receipt`. That is correct: the restarted gateway must load the just-published bridge, which always writes `source`. Rollback to the managed runtime does not call `verify_registration`, so an older managed bridge does not need the field.
- `hermes_cli` as a stub module without `__file__` records `None` (test covers it).

### Focus 4: `.env` block boundary

- `before` ends with `\n` or `\r\n`: no separator, unchanged behaviour.
- `before` unterminated, `after` present: `\n` inserted. `before` unterminated, `after` empty: no separator; `_sanitize_env_lines` terminates the line. Both tested.
- `before` ends with a lone `\r`: no separator; `io.StringIO(newline=None)` treats the lone `\r` as a line end, so the following owner line stays separate.
- Block at the start: `before` empty, no separator, `after` intact.
- Ambiguity check (`count > 1`) runs before the partition. No problem.

### Focus 5: probe and failure records

- `PROBE_CODE` runs inside `runtime_command`'s bootstrap, which has already done `import os, sys, runpy` and `import hermes_bootstrap`, so `sys` exists and `sys.dont_write_bytecode=True` precedes the import of the retained bridge. `hermes_bootstrap` bytecode can land in the Hermes checkout's `__pycache__`, not in the retained bridge; `fingerprint` excludes `__pycache__` and `.pyc` by default and `runtime_source_fingerprint` uses it, so the retained stock runtime for the removal probe is unaffected. The bytecode test exercises exactly this.
- `probe_failure` forwards a message only when the last stderr line is `...memory_access.MemoryUnavailable: The ...`. I listed every `MemoryUnavailable` with dynamic content in the bridge: `"Native memory operation failed: " + stderr[:500]`, the `Atlas capacity` f-strings, and `f"LifeOS {name} is outside..."`. None starts with `The `, so they fall back to the generic text. The only dynamic content that can pass is `type(error).__name__` from the probe itself, a class name.
- `record_probe_output` writes the last 64 stderr lines with mode 0600 into the private job directory next to `request.json`. The agent's own stdout and stderr are captured in the probe's `diagnostics` buffer and never emitted, so the tail holds tracebacks and import-time output. Tracebacks carry source lines, not values. Same trust level as the rest of the job directory.
- `worker-failure.json`: exception type, frames (file, line, function), and the message only for `ReleaseRejected`. It is written to `args.job` before `_job` validates the identifier, but the manager supplies that path and `publish` requires a physical parent directory. No credential or memory content path.

### Commit b19e793e

`_run` uses 300 s for `stop`, `start`, `restart` and 45 s otherwise. The stock gateway's `TimeoutStopSec` is the restart drain plus the cron drain (70 s by default); 300 s covers it with margin. The drain test with a 46 s stop proves the wait. No problem beyond finding 6.

## Tests

Focused files pass (`focused-tests.txt`): `test_inplace_preparation.py` 13, `test_removal_configuration.py` 8, `test_memory_workflow_failures.py` 5, `test_bridge_registration.py` 6. I did not run `test_profile_services.py` because it drives real user units and a full suite was already running. The adoption tests there modify the unit file and run `daemon-reload` before adopting, so they do not cover finding 1, and they change only the fragment, so they do not cover finding 2.

## What the e2e runs do not cover

- Crash recovery on a transition host (the matrix ran on 112, a fresh install). Finding 1 lives there.
- A transition from a host whose gateway unit came from the LifeOS template. Host 114's unit was in stock format (its `ExecStart` carried the managed checkout path, which is what defect 2 described). Finding 2 lives there.
