> Primary integration note: the code commit is integrated as `a4c93955`. The broad worker runs below retain their original failures. The primary repeats 150 release checks with the frozen native fixture, then passes all eight process-boundary cases under a disposable local account. See the [combined verification](../2026-10-16-codebase-cleanup/codebase-cleanup.md) for counts, skips, fixture cleanup, and qualification limits.

# Release tooling cleanup

- Date: 2026-10-16
- Agent role: cleanup implementer for installation, update, recovery, and package tooling (release-cleanup worktree)
- Question: Which unused imports, dead code, repeated logic, or avoidable indirection in the owned release-manager, script, and bridge installation modules can be removed or simplified without changing behavior? Why do the two lifecycle patch copies drift, and what small follow-up would stop it?
- Model: Claude Opus 5.5 (`claude-opus-5-5`)
- Starting commit: `728cd17a94607ec4c119419c052060582a8b75af`
- Code commit: `d3448f91bde905ae54ba08293d78af033b38ad10` (`refactor(release): share launcher script bytes`)

The primary preserves the original `checks.txt`, `data.diff`, and worker report inside [evidence.tar.gz](evidence.tar.gz). Extract that archive into a disposable directory to inspect them. The worker diff can also be regenerated with `git diff 728cd17a94607ec4c119419c052060582a8b75af d3448f91bde905ae54ba08293d78af033b38ad10`.

## Changes

| File | Change | Proof that it preserves behavior |
| --- | --- | --- |
| `optional/lifeos_release_manager/dashboard/plugin_api.py` | Removed `import os` | No `os` name in the module; no `plugin_api.os` reference anywhere |
| `optional/lifeos_release_manager/release_payload.py` | Removed `import json` | No `json` name in the module; the file is also run by path through `spec_from_file_location`, which does not read module attributes other than `assemble_runtime` |
| `optional/lifeos_release_manager/removal_generation.py` | Removed `import json`, `import os`, and (after the helper change) `import shlex` | No remaining uses; no external attribute access |
| `optional/lifeos_release_manager/removal_services.py` | Removed `import os` | No `os` name in the module |
| `optional/lifeos_release_manager/removal_workflow.py` | Removed `import hashlib` | No `hashlib` name in the module |
| `optional/lifeos_release_manager/release_worker.py` | Removed the local `active_bridge` in `_execute` (assigned, never read since commit `be215380`), and `import shlex` after the helper change | Pure `Path` join with no side effect |
| `optional/lifeos_release_manager/release_programs.py` | Added `launcher_script(command)` | Returns the exact bytes the five sites built inline |
| `release_worker.py` (2 sites), `removal_generation.py` (2 sites), `removal_preparation.py` (1 site) | Use `launcher_script` | Same expression; each call site keeps its own `str(...)` conversion, so a non-string runtime value still raises `TypeError` at `release_worker.py` as before |
| `scripts/clarify_fixture_host.py` | Removed `import threading` | Unused; no recorded hash of this file anywhere |
| `scripts/probe_installed_context.py` | Removed `import sys` | Unused; no recorded hash of this file anywhere |

Tests added or strengthened (characterization first, then the helper test written before the helper):

- `tests/test_release_programs.py`: `test_launcher_script_quotes_one_command_and_forwards_arguments` pins exact bytes for a plain path, a path with a space and a single quote, and the `TypeError` for a `Path` argument.
- `tests/test_removal_generation.py`: new `GenerationLauncherTests` class.
  - `test_wrapper_accepts_only_the_exact_quoted_launcher` covers `_wrapper` (line 31).
  - `test_generation_is_selected_only_by_its_exact_account_launcher` covers the candidate filter in `selected()` (line 55). It uses a small stub bridge that reports a verified active bridge. The matching case reaches the next step and raises `KeyError('certificate')`; the non-matching case raises the selection refusal.
- `tests/test_release_configuration.py`: `test_program_plan_stages_the_runtime_launcher_before_command_checks` covers `release_worker.py:189` through the error path.
- `tests/test_removal_preparation.py`: `test_fixed_plan_keeps_data_and_prompt_and_uses_stock_launchers` now asserts exact launcher bytes and mode `0o700` (line 64).

Each launcher site was mutated on the starting-commit code (append one space before the trailing newline). Before the new tests, only `release_worker.py:197` was detected. After them, all five mutations fail their test, and all tests pass unmutated. See "Mutation coverage" in checks.txt.

## Why the launcher helper is worth it

`release_worker._program_plan` and `removal_preparation.software` write account launchers. `removal_generation._wrapper` and `selected()` admit a removal only when the installed launcher bytes equal the expected bytes. Before this change, the writer and the verifier each spelled out the format. A one-character edit on one side would make removal refuse every managed installation, and no test caught that at three of the five sites. One function now owns the format. `removal_preparation._recovery_command` still builds its own script because it uses `shlex.join` over an argument list; that is a different format and I left it.

## Safety reasoning

- No lease, lock, service drain or restart order, fsync, journal, recovery check, owner grant, or immutable asset path changed. `publish` calls keep the same targets, data, and modes.
- No patch bytes, patch lists, source revisions, or version declarations changed.
- The release manager is copied as a whole directory (`cli.py` copies the package directory to `job/worker`; removal copies the installed manager to `removal/recovery-manager`) and validated against `manager_files`. A new function inside `release_programs.py` therefore never meets an older `release_programs.py` from another release.
- `removal_bootstrap.py` is read as source text and executed standalone; I did not touch it.
- Bridge modules in my scope are reached by the release manager through `memory_module(...)`, including private names (`update_plan._digest`, `profile_services._digest`, `update_dependencies._package_roots`, `mount_transaction._read`). I made no bridge edits.

## Tests

Interpreter: `/tmp/rc-tools/venvpy`, which runs the existing venv `/home/outsider/.cache/hermes-upstream-tests-e49a6af/bin/python` (fastapi, starlette, ruamel) with `PYTHONPATH`, `LIFEOS_HERMES_SOURCE`, and `LIFEOS_MEMORY_SOURCE` pointing at scratch copies of the 0.7.2 package's prepared `hermes/` and `lifeos/LifeOS/install`, and `PYTHONDONTWRITEBYTECODE=1`. Nothing was installed. The full wrapper text is in checks.txt.

Command, run once per file from the tested root:

```bash
/tmp/rc-tools/venvpy -m unittest discover -s tests -p '<file>.py'
```

67 files (all `test_release_*`, `test_removal_*`, `test_update_*`, `test_install*`, `test_selection_*`, `test_profile_*`, and the related mount, lock, drift, stock, patch, source, portability, hook-evidence, and step-1 acceptance files; full list in checks.txt). `discover -s tests` is needed because these suites import sibling test modules by top-level name.

| Run | Tests | Failures | Errors | Skipped | Files OK / failed |
| --- | --- | --- | --- | --- | --- |
| Baseline, start commit (`/tmp/rc-base` export) | 529 | 31 | 54 | 25 | 54 / 13 |
| Final, this worktree | 533 | 30 | 54 | 24 | 55 / 12 |

Differences between the runs:

- +4 tests from this change (`test_release_configuration` 7 to 8, `test_release_programs` 22 to 23, `test_removal_generation` 3 to 5). All pass.
- `test_hook_evidence` (one skip) and `test_prepare_sources` (one failure) differ only because `/tmp/rc-base` is not a Git checkout. At the start commit in a Git clone they give `Ran 10 tests OK` and `Ran 4 tests OK (skipped=1)`, the same as final.

The 12 files that fail in both runs fail with identical counts. Causes, all pre-existing and environmental or known:

- The prepared LifeOS source lacks Bun packages (`yaml`, `smol-toml`, `@anthropic-ai/claude-agent-sdk`): `test_installation_lease`, `test_memory_portability_lifecycle`, `test_profile_backup`, `test_profile_backup_recovery`, `test_removal_preparation` (3 of 8), `test_optional_text_release`, and native mount preparation in `test_mount_transaction` and `test_memory_admin_install`.
- `test_patch_bundle`: the known lifecycle patch mismatch (see below).
- `test_removal_consumers`: `PermissionError` on `/proc/<pid>/exe` for a process outside the account boundary.
- `test_removal_coordinator` (4 failures, "The actual coordinator does not save its result") and `test_removal_data_barrier` (1 failure): not investigated; identical before and after.
- `test_profile_backup` also has 4 `ModuleNotFoundError: lifeos_hook_bridge` in child processes.

Other checks:

- `python3 scripts/check_hook_evidence.py`: exit 1 at baseline and final, byte-identical output (pre-existing changed artifacts such as `bridge.py`, `install_source.py`, `prepare_sources.py`). No file whose hash still matches the ledger was edited.
- `python3 -m py_compile` on every changed `.py` file: ok.
- `git diff --check`: ok. No em dash in changed files.
- I did not run `node --test` because no JavaScript or CSS changed.

The system `python3` baseline is also recorded in checks.txt for context. It lacks Hermes, ruamel, and fastapi, so most release suites error there; I did not repeat it for the final tree.

## Candidates rejected or deferred

Syntactic candidates are names a static scan reports as unused. Proved dead code is a candidate whose callers I traced through dynamic imports, path-launched workers, CLI and dashboard callers, package inputs, recorded evidence hashes, and tests.

| Candidate | Status | Reason |
| --- | --- | --- |
| The 6 imports named in the task, plus `shlex` in two files after the helper change | Proved dead, removed | See Changes |
| `release_worker._execute` local `active_bridge` | Proved dead, removed | Never read since it was added |
| `scripts/evaluation_operation_controls.py` `base64`, `scripts/native_inference_effect_controls.py` `time` | Syntactically unused, deferred | `docs/parity/handler-effects.json` pins their current SHA-256, and `scripts/check_hook_evidence.py` reports any change as `changed artifact`. Editing them would add a new gate failure and break the link to the parity evidence |
| `scripts/batch_patch_fixture.py` `shlex`; `installed_external_safety_controls.py` `sys`; `installed_update_controls.py` `sys`; `managed_context_delivery_controls.py` `shlex`, `sys` | Syntactically unused, deferred | Their current bytes are the recorded code identity in dated acceptance records (`docs/verification/2026-10-07-step1/installed-release-controls/current-code-identity.json`, `2026-10-06-hook-completion/runtime-check.json`). Removing an unused import has no functional value and makes those records no longer match the active script |
| `scripts/probe_file_rewrite_installed.py` `file_tools`; `scripts/run_live_remote_gate.py` `hermes_bootstrap` | Not dead | Side-effect imports (tool registration; managed dependency bootstrap, marked `noqa`) |
| `stock_hermes.verify_source` | Unused by product code, kept | Imported by dated operators `docs/verification/2026-10-15-memory-portability/construct_stock_runtime.py` and `verify_constructed_stock_source.py`, and tested. Removing it breaks re-running that evidence |
| `scripts/release_transaction.py` and `lifeos_hook_bridge/update_transaction.py` | Live | Older transaction tools still have callers (`update_worker.py`, `dashboard/plugin_api.py`, `scripts/installed_update_controls.py`, tests, the rehearsal note's restore command) |
| Repeated `_digest` helpers in `update_plan.py`, `update_dependencies.py`, `version_drift.py`, `update_worker.py`, `profile_services.py` | Kept | The release manager calls `update_plan._digest` and `profile_services._digest` dynamically. `version_drift.py` is executed standalone by `bin/git` and `bin/version-drift-baseline` and cannot import siblings |
| Canonical JSON signing (`json.dumps(sort_keys, separators=(',',':'))`) repeated in `memory_workflow`, `removal_preparation`, `removal_workflow`, `removal_services`, `removal_state` (3 times), `removal_bootstrap` | Deferred | Same writer and verifier pattern as the launcher bytes, but `removal_bootstrap.py` must keep its own copy because it runs standalone, so a helper cannot fully unify it. It touches 5 signature files for partial gain. Worth a separate small change with its own characterization tests |
| `release_stage.prepare_runtime` `helpers = load_bridge(...)` | Kept | Name is unused, but the call imports the package's `install_source` and sets `sys.dont_write_bytecode`. Removing the call changes behavior; dropping only the name adds nothing |
| `release_worker.py:189` `publish(launch, ...)` | Kept, reported | The loop at line 197 always rewrites the same `generated/hermes` path. The first write is visible only when the command check raises. It is a redundant write plus fsync, not dead code, and I did not remove a publish from the release worker |
| `removal_services._run` and `_identity` both call `import_module(type(self.services).__module__)` | Rejected | Two lines; a helper adds indirection for no clarity |
| Unused tuple-unpacked locals (`source`, `configuration`, `value`, `selected`, `request`) in `plugin_api.owner`, `review_release`, `cli.launch`, `removal_recovery.main`, `removal_workflow` | Rejected | The calls validate and raise; renaming to `_` is cosmetic |
| Bridge-owned modules (`install_source`, `installation_selection`, `lifeos_installation`, `native_dependencies`, `mount_transaction`, `program_lock`, `profile_*`, `release_version`, `update_*`, `version_drift`) | No change | No unused imports; every module-level definition has a production caller (scan in checks.txt) |

## Lifecycle patch drift audit

Facts:

- Only `hermes-session-lifecycle.patch` differs between `patches/` and `lifeos_hook_bridge/patches/`. The two patch name sets and both ordered lists (`install_source.HERMES_PATCHES` and `LIFEOS_PATCHES`, `scripts/prepare_sources.SOURCES`) are currently equal, as are the base revisions.
- The copies diverged in commits `3634f58b` (`fix(discord): preserve first-turn admission`) and `3cfddbfc` (`fix(discord): resolve mirror review findings`, 0.7.1). Both changed only the distributed copy. The development copy last changed in `be215380`.
- `scripts/rebuild_hermes_patches.py` writes to one `--output` directory. `docs/patch-footprint.md` step 4 shows a single `--output PATH`. A regeneration therefore updates one copy unless the person runs it twice.
- `tests/test_patch_bundle.py` already compares both copies byte for byte and fails now. Records up to 2026-10-14 mention it (test logs on 2026-09-29, later mostly as a hashed file in identity maps). No record dated 2026-10-15 or 2026-10-16 mentions it, and the divergent commits are dated 2026-10-16, so the 0.7.1 and 0.7.2 qualification evidence does not show this guard running.
- The lists are declared twice (`install_source.py` and `prepare_sources.py`). They agree today only because the same test checks them.

Proposed follow-up (not implemented; it would change patch bytes or tooling behavior):

1. Regenerate or copy the distributed `hermes-session-lifecycle.patch` into `patches/`, then re-prepare from the pinned bases and run the lifecycle behavior tests. This is the TODO item.
2. Make `rebuild_hermes_patches.py` write each group to both `patches/` and `lifeos_hook_bridge/patches/` (or refuse when they differ afterwards). One file, one test.
3. Make `scripts/prepare_sources.py` import `SUPPORTED_*_COMMIT` and `*_PATCHES` from `lifeos_hook_bridge.install_source` instead of repeating them, so only the bytes can drift.
4. Add `python -m unittest discover -s tests -p 'test_patch_bundle.py'` to the release qualification command list so a byte mismatch blocks a release.

Steps 2 to 4 do not depend on step 1 and are each small. Step 1 is the only one that changes behavior.

## Scope inventory

Inspected in full or by targeted reading:

- `optional/lifeos_release_manager/`: all 33 tracked Python files scanned by AST for unused imports, unreferenced definitions, and unused locals. Read in detail: `dashboard/plugin_api.py`, `cli.py` (lines 1 to 262), `release_payload.py`, `release_programs.py` (header), `release_stage.py` (`load_bridge`, `prepare_runtime`), `release_worker.py` (header, `_program_plan`, `_execute`), `removal_generation.py`, `removal_workflow.py`, `removal_services.py`, `removal_preparation.py` (`software`, `_encoded`, `_recovery_command`), `stock_hermes.py` (`verify_source`), `release_accounts.py`.
- `scripts/`: all 45 Python files scanned by AST. Read: `build_managed_release.py`, `prepare_sources.py`, `rebuild_hermes_patches.py` (`rebuild`, CLI), `check_hook_evidence.py` (artifact and acceptance checks), the import blocks of every flagged script.
- Bridge modules in scope (16 files): scanned by AST; read the headers of the `update_*` modules and `version_drift` callers; traced every `memory_module(...)` attribute access from the release manager.
- Evidence: `docs/parity/handler-effects.json` and `step1-acceptance.json` artifact hashes for owned files; recorded hashes of each flagged script across the repository.

Not inspected in detail: most function bodies in `release_worker.py`, `release_plan.py`, `release_operation.py`, `release_services.py`, `release_catalog.py`, `release_initialization.py`, `memory_workflow.py`, `removal_publication.py`, `removal_consumers.py`, `removal_inventory.py`, `removal_state.py`, and the 2,345-line `scripts/paired_lifecycle_effects.py`; the bridge modules `install_source.py`, `mount_transaction.py`, `profile_backup.py`, `profile_services.py`, `update_transaction.py` beyond callers and imports. For those, the review covered static unused-name detection and caller tracing, not logic-level simplification.

## Remaining review concerns

1. Riskiest change: the launcher helper touches byte formats that removal admission compares. All five sites are now mutation-tested, and the helper test pins quoting for spaces and single quotes.
2. `test_removal_generation.test_generation_is_selected_only_by_its_exact_account_launcher` uses a stub bridge and asserts `KeyError('certificate')` as the sign that selection passed. It describes current behavior; a later change to the step after selection will need this assertion updated.
3. Decision not specified by the task: I did not edit scripts whose current bytes are recorded in evidence, even when the import is unused.
4. Not covered: the three `test_removal_preparation` tests and other native suites that need Bun packages in the prepared LifeOS source, and the `test_removal_coordinator` failures. They fail identically before and after.
5. Test hygiene bug, not fixed (outside the cleanup): `test_memory_portability_lifecycle` leaves 12 synthetic user units when its native setup fails, and earlier failing runs left unit files in `~/.config/systemd/user`. These tests run against the real user service manager.

### Changes outside Git

- My first venv baseline put the 0.7.2 package's `hermes/` directly on `PYTHONPATH`. Test processes wrote 121 files into `/home/outsider/.cache/lifeos-release-0.7.2-20261016/packages/0.7.2-b257d29f/hermes/` (120 `.pyc` files in 50 new `__pycache__` directories, plus `.bytecode-fingerprint`). None of these existed before, and the `.tgz` archive and source manifest contain none. I removed exactly those files and directories; no file newer than the run start remains. Directory mtimes stay changed. The `.tgz` archive was not touched. Later runs used copies in `/tmp/rc-src`.
- I stopped and removed the synthetic `lifeos-ownership-test-*` units and `/tmp/native-memory-*` fixture directories that my runs leaked, selected by command line or unit file referencing my test roots. Three failed units from 2026-10-15 are not mine and remain.
- Scratch data outside the repository: `/tmp/rc-tools` (runner scripts and logs), `/tmp/rc-src` (355 MB source copies), `/tmp/rc-base`, `/tmp/rc-git`, `/tmp/rc-scan`. Delete them with `rm -rf` when no longer needed.
