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

## Round 2 (commits 8d009e25 and 29c8d94c)

Reviewed 2026-10-17 by the same independent reviewer (Claude Fable 5.1). Raw data: `round2-diff.patch`, `round2-focused-tests.txt` (`test_inplace_preparation.py` 19 tests, `test_release_accounts.py` 8 tests, all pass).

### Round 1 findings: status

- Finding 1 (NeedDaemonReload): fixed. `adopt_units` (`inplace_worker.py` lines 132 to 142) runs `daemon-reload` before adoption when the request has transition units. It is the first call in `_rollback` and in the recover branch, so the reload precedes `_quiesce` and `programs.restore()` as well. When `transition_units` is empty no unit file is in the transaction, so skipping the reload is correct.
- Finding 2 (KillMode): fixed. `transition_gateway_unit` (`inplace_preparation.py` lines 85 to 119) returns `{}` unless the gateway fragment contains `/.lifeos-releases/`, and refuses a replacement whose `KillMode` or `WorkingDirectory` text differs. The refusal now happens before publication, so the stuck state is unreachable from this cause. See R2-2 for the one gap in the text comparison.
- Finding 3 (symlink): fixed, refused at preparation.
- Finding 4 (drop-ins): fixed. `_unit_texts` scans the fragment and `<unit>.d/*.conf` for all three units, with the gateway fragment exempt because it is the file being replaced.
- Finding 5 (stderr): fixed, last stderr line, capped at 300 characters, appended to the refusal.
- Finding 6 (90 s timeouts): not addressed; still minor.

### Answers to the three questions

(a) Reading `running_source().parent / plan.json` is sound for the decision it makes. `transition_source` (`host_compatibility.py` lines 421 to 433) already derives the transition itself from `running_source()`, and it requires the shape `<profile>/.lifeos-releases/<32 hex>/hermes`, so `running_source().parent` is a managed job directory by construction. The running source can differ from the active managed job in one way: a stale process, for example a gateway that was not restarted after a managed update, or a hand-started shell from an older job. In that case the launchers on disk forward to the newer job, `str(job) not in path.read_text()` is true, and `managed_service_launchers` refuses. The failure direction is safe; only the message is wrong (R2-4). The reverse direction, accepting launchers that forward elsewhere, cannot happen because the content check binds each launcher to this job. Two gaps are in R2-3.

(b) Mechanically, publishing a forwarder into the workspace checkout's `.hermes/bin/hermes` is fine for `ProgramTransaction`: the entry is a regular file, `before` is the managed forwarder with its mode, `after` is the stock forwarder (mode 0755 from `publish`), `_check_publication` refuses at apply when the owner changed the file after preparation, and `restore()` writes the managed forwarder back with the recorded mode. `.hermes/` is ignored by the Hermes checkout (`.gitignore` line 174), so the workspace's `git status` stays clean. The problem is ownership: that path belongs to the workspace checkout's own Hermes, which rewrites `.hermes/bin` launchers on `hermes update` and on launch-time self-heal (`.gitignore` lines 264 to 266 say so, and `_launchers.py` `_owns_launcher` will not recognise the stock forwarder as its own). See R2-1.

(c) The text comparison can disagree with systemd in both directions, but only one direction matters. False refusals (text differs, systemd equal): `WorkingDirectory=~`, `%h/...`, a `-` or `!` prefix, a quoted value, a continuation line. All of these refuse a transition that would have worked; the message points the owner to `hermes gateway install`, which rewrites the unit in the stock form, so the owner can get past it. False acceptance (text equal, systemd differs): `_service_value` ignores section headers, so a `KillMode=` line under `[Unit]` or `[Install]` is counted although systemd ignores it (R2-2). Drop-ins do not create a disagreement: `_service_value` reads only the fragment, and a drop-in applies to both the existing and the replacement unit equally.

### Findings

#### R2-1. should-fix (medium): the workspace checkout's own Hermes will overwrite the published forwarder

Files: `inplace_plan.py` lines 164 to 181 (`transition_launchers`, `services` loop), `inplace_preparation.py` lines 65 to 82 (`managed_service_launchers`).

Scenario: on the development host, the transition publishes `exec ~/.hermes/hermes-agent/.hermes/bin/hermes "$@"` at `~/workspace/hermes-agent/.hermes/bin/hermes`. Later, Adrian runs anything that executes the workspace checkout's own Python entry points (`install.sh`, `uv run hermes`, `python -m hermes_cli.main update` from that checkout). Hermes rewrites `.hermes/bin/hermes` with its own launcher. From the next gateway restart, `hermes-gateway.service` and `hermes-dashboard.service` run the workspace checkout, not the installation; no LifeOS code notices until the next operation runs `check_receipt`. A later restore of the transition refuses with `Program recovery preserves a later artifact edit` (`release_programs.py` line 364) because the target no longer matches `after`.

The managed release already lived with this risk for the same file, so the transition does not make it worse; it keeps a known trap on a host where the checkout is actively developed. Options, in order of preference:

1. Refuse at preparation with the same instruction the code gives for other units: "point `hermes-gateway.service` and `hermes-dashboard.service` at `~/.local/bin/hermes`", and let the owner edit the two `ExecStart` lines once. After that, `~/.local/bin/hermes` is the only launcher the transition manages, and the workspace checkout is left alone. This is one owner step and removes the class of problem.
2. Keep the publication, and document in the design (section 10) that running the workspace checkout's installer or updater detaches the services from the installation until the owner re-runs the transition or edits the units.

#### R2-2. minor: `_service_value` ignores unit sections

File: `inplace_preparation.py` lines 58 to 61. A `KillMode=` or `WorkingDirectory=` line outside `[Service]` is counted although systemd ignores it. Example: existing unit has `[Unit]\nKillMode=mixed` and no `KillMode` under `[Service]` (systemd default `control-group`); the generated unit has `KillMode=mixed` under `[Service]`; the texts compare equal, the transition proceeds, and `adopt_definition` refuses after publication, which is the stuck chain from round 1 finding 2. This needs an owner-authored mis-sectioned key, so it is unlikely. Fix: track the current `[section]` while scanning and consider lines only inside `[Service]`.

#### R2-3. minor: two silent paths in `managed_service_launchers`

File: `inplace_preparation.py` lines 65 to 82.

- A missing `plan.json` raises `FileNotFoundError` from `_json(...read_bytes())`. `cli.prepare` records `preparation_failed` with the generic reason instead of a refusal text. Fix: catch `OSError` and raise `ReleaseRejected('The managed release has no plan record')`.
- A `plan.json` without `launchers` yields `[]`, so nothing is repointed; the units keep forwarding to the managed job and `check_receipt` rolls the operation back after the restart. Every managed plan this code base writes has `launchers` (`release_worker.py` line 46), so this is defensive only. Fix: refuse when the key is missing rather than defaulting to `[]`.

#### R2-4. minor: the stale-process refusal blames the owner

File: `inplace_preparation.py` line 80. When the preparing process imports an older managed job (see answer a), the message says the launcher "no longer runs the managed release" and the docstring says "its owner changed it". The likelier cause is a gateway that was not restarted after a managed update. Fix: name both causes in the message, or compare against the job that `~/.local/bin/hermes` forwards to and report which job each side names.

#### R2-5. minor: the rewritten account test asserts little

File: `tests/test_release_accounts.py` lines 123 to 153 (commit 29c8d94c). The test now stops at `download_integration` and asserts that `account_home` was called once with the profile and that the selection bytes are unchanged. It no longer checks that the request records `account_home`, `installed`, or `profile`, because the request is written after the download. That coverage is lost rather than moved. The in-place request fields are exercised indirectly by the container runs; a unit test would need a catalog stub that returns a package, which `ReleaseStageTests().package` already provides for the managed path.

### Checked and found no problem

- `adopt_units`: the reload runs under the same conditions as the adoption and before every `_quiesce` and `programs.restore()` that follows it. `_systemctl('daemon-reload')` raising inside `_rollback` aborts the rollback, but the same call already sat at line 226 with the same effect.
- `transition_gateway_unit`: the `/.lifeos-releases/` test on the gateway fragment matches how a managed `hermes gateway install` writes the unit (host 114) and leaves template units (`~/.local/bin/hermes`) alone, which `transition_launchers` repoints. The `KillMode` default `control-group` matches systemd's default. The generated unit always sets `WorkingDirectory`, so a template unit without one refuses, which is correct because `ProfileServices` binds the working directory.
- `managed_service_launchers`: `plan.json` launchers come from the gateway and dashboard `ExecStart` executables, restricted to regular files under the account home (`release_plan.py` lines 71 to 82), so the `hermes` forwarder is the right content for each. The `~/.local/bin` exclusion compares the unresolved parent, and `plan.json` stores the path as systemd reported it, so the exclusion holds for the paths this code base writes.
- `transition_launchers(services=...)`: several targets share `generated/launcher-hermes`; `ProgramTransaction.prepare` copies the source per entry (`incoming-<index>`), so sharing is fine.
- Tests: the new tests cover the account-launcher unit, the KillMode refusal, the drop-in refusal, the symlink refusal, the reload before adoption, launcher selection with a changed launcher, and forwarder publication. They do not cover R2-2 (mis-sectioned key) or R2-3.
