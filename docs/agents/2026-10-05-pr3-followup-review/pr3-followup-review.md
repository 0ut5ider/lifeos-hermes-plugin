# PR 3 follow-up review: commits 71987ce..c083037

- Date: 2026-10-05
- Role: independent follow-up reviewer of post-review commits (security focus)
- Model: Claude Opus (claude-opus-5-5)
- Repository: /home/outsider/Projects/Hermes_agent/LifeOS_plugin, branch feature/hook-compatibility-evidence, pull request #3
- Question: Do commits feebc71, b37cc07, and c083037 introduce security defects or behavior regressions? Focus areas: (A) the sharing component loader and installer, (B) regressions from moving SSH enrollment out of the package, (C) the fresh_store lock change, (D) the memory_provider registration change, (E) whether the new tests test what they claim.

Method: I read all code at c083037 through git (`git show`, `git diff`). I exported c083037 to /tmp/pr3review/src with `git archive` and ran small experiments there against the real loader and installer code. I did not run the project test suites. I changed nothing in the repository except this directory. Experiment scripts and their output are in this directory (`exp*.py`, `exp*.sh`, `exp*_output.txt`). Python version for the experiments: 3.14.7.

## Findings, most severe first

### 1. A planted bytecode cache file runs instead of the hash-verified source (Medium, confirmed by experiment)

- Location: `lifeos_hook_bridge/memory_preferences.py:43-51` (`load_sharing_component`).
- Defect: The loader hashes `memory_sharing.py`, then imports it through `spec_from_file_location`, which uses `SourceFileLoader`. That loader prefers `<component>/__pycache__/memory_sharing.cpython-3XX.pyc` when the cache is valid, and the loader never checks the `__pycache__` directory or the cache file.
- Scenario: Anyone who can write into `<component>/__pycache__` places either (a) an unchecked hash-based pyc, which Python never compares with the source, or (b) a timestamp pyc whose header copies the source mtime and size (both are readable with `stat`). The next dashboard page load executes the planted code in the dashboard process, which can write `~/.ssh/authorized_keys`. The SHA-256 pin is satisfied the whole time.
- Exposure: The loader itself creates `__pycache__` on the first load with mode `0777 & ~umask`. Under umask 002 (the Fedora default for user private groups when the user name equals the group name), the directory is `0775`. `install.py` neither removes nor re-permissions an existing `__pycache__`, and `--remove` leaves it behind (finding 4). In a single-user setup with a private group, only the owner can write there, so practical exploitability is low. But the pin's stated guarantee ("the file hash equals the hash that this plugin release records" in the README) does not hold for the code that actually runs.
- Evidence: `exp1_pycache_override.py`, `exp1_output.txt`: both variants print `PLANTED`; a normal load under umask 002 creates `__pycache__` with mode `0o775`.
- Fix direction (one change also fixes finding 2): read the bytes once, verify the hash on those bytes, then `exec(compile(data, str(source), 'exec'), module.__dict__)` on the module created from the spec. This removes the second file open and never consults or writes a bytecode cache.

### 2. Time of check versus time of use: the source is opened twice, and the parent directory is not checked (Medium-low, confirmed by simulated race)

- Location: `lifeos_hook_bridge/memory_preferences.py:37-51`.
- Defect: The loader checks `lstat` of the directory and file, hashes `source.read_bytes()`, then `exec_module` opens the path again through normal path resolution. Nothing ties the executed bytes to the hashed bytes. The loader also does not check the parent directory (the Hermes home). `install.py:target()` does check the profile for group and world write, so the loader is weaker than the installer.
- Scenario: The Hermes home is group-writable or world-writable (the loader accepts this). An attacker with write access to it renames `lifeos-memory-sharing` away right after the hash and puts an attacker-owned directory with the same name in its place. `exec_module` runs the attacker's `memory_sharing.py`.
- Evidence: `exp2_toctou_swap.py`, `exp2_output.txt`: with the swap injected immediately after the digest, the output is `SWAPPED CODE RAN`, with a `0777` parent accepted. The swap is injected by a stand-in for `hashlib`. I did not run a real concurrent race, but the window is the same.
- Precondition is a misconfigured Hermes home, so severity is limited. The fix from finding 1 closes it. Optionally also apply the installer's parent check to the loader.

### 3. Fallback revocation leaves the SSH entry, and the dashboard then hides the only way to remove it (Low-Medium, confirmed by reading)

- Locations: `lifeos_hook_bridge/memory_preferences.py:274-287` (`revoke`), `lifeos_hook_bridge/dashboard/dist/index.js:96` and `:245-247`, `optional/lifeos-memory-sharing/README.md:31`.
- Defect: Without a loadable component, `revoke` only sets `enabled: false` and returns `credential_entry_removed: False`. The UI ignores that field and shows "Connection revoked. Its contributed facts remain." The UI renders the Revoke button only when `connection.enabled` is true, so after a fallback revocation the button is gone. The README says to "reinstall the component and revoke again", but the dashboard offers no control to do that. Only a direct `DELETE /connections/<client>` API call or a manual edit of `authorized_keys` removes the entry.
- Silent trigger: The fallback runs whenever `load_sharing_component` raises `MemoryUnavailable`. That includes a component that is present but has a stale hash after a plugin update, not only an absent component. The operator who revokes during that window gets a success message and a stale key line.
- Impact: Limited. `MemoryService.client_scope` (`memory_service.py:552-555`) refuses a disabled grant, and the entry is `restrict,command=...`, so the stale key can only start a memory process that refuses every request. The client name also cannot be reused. This is a correctness and documentation defect, not data exposure.
- Before this change, every revoke removed the SSH line. That behavior now silently depends on component state.

### 4. `install.py --remove` follows a symlinked component directory and deletes a file outside it, and it leaves the bytecode cache behind (Low, confirmed by experiment)

- Location: `optional/lifeos-memory-sharing/install.py:42-50` (`remove`).
- Defect: `remove` checks the profile, but not whether `lifeos-memory-sharing` is a physical directory. `program.exists()` and `program.unlink()` resolve through a symlinked directory. `directory.rmdir()` then fails on the symlink, and the bare `except OSError: pass` swallows the failure.
- Scenario: If `~/.hermes/lifeos-memory-sharing` is a symlink to some other directory, `--remove` deletes `memory_sharing.py` in that other directory and prints "Removed the sharing component". Creating that symlink needs owner write access to the profile, so this is a robustness defect, not an attack.
- Second defect: After any load, the directory contains `__pycache__/memory_sharing.cpython-3XX.pyc`. `rmdir` fails silently, so the directory and the compiled component stay while the script reports removal. The README says "Removal deletes the installed program". The compiled program remains, although Python will not import it without the source.
- Evidence: `exp3_installer_symlinks.sh`, `exp3_output.txt`, cases 3d and 3e. Note: the `exit=` values in that output are the exit codes of `tail`, not of the installer. The installer messages are the relevant lines.
- The install path is sound: a symlinked component directory is refused with `SystemExit` (3a), a dangling symlink fails with `FileExistsError` before any write (3b), and a symlinked `memory_sharing.py` is replaced as a link without writing through to the target (3c).

### 5. On an unsupported host middleware version, a malformed configuration now aborts the whole plugin even when lasting memory is disabled (Low, confirmed by experiment)

- Location: `lifeos_hook_bridge/memory_provider.py:111-112`, `lifeos_hook_bridge/memory_runtime.py:107-110`, `lifeos_hook_bridge/__init__.py:22-24`.
- Defect: `MemoryRuntime.enabled()` calls `MemoryConfiguration.load()`, which raises `MemoryUnavailable` (for group-readable permissions, a symlink, or a non-file) and `ValueError`/`JSONDecodeError` (for invalid content). In the new `elif` branch, that exception escapes `register_provider`. `register()` in `__init__.py` does not catch it, so none of the LifeOS hooks register either.
- Scope: This branch runs only when `hermes_cli.middleware.REQUIRED_MIDDLEWARE_API_VERSION != 1`. Current hosts report 1, so today's users are not affected. A future host bump plus a configuration with, for example, mode 0644 and `ownership_enabled: false` would disable the hook bridge entirely. An absent configuration and a valid configuration with ownership disabled both register normally.
- Evidence: `exp5_error_paths.py`, `exp5_output.txt`, case 5b: `absent` and `valid, ownership disabled` return; `0644` raises `MemoryUnavailable`; truncated JSON raises `JSONDecodeError`.
- The same pattern already existed in the `ImportError` branch before this change. The raise occurs after `ctx.register_memory_provider(provider)`. I do not know whether Hermes rolls back a partial registration when `register()` raises. If it does not, the provider is still fail-closed, because `is_available()` requires version 1.
- Fix direction: catch the load errors around `enabled()` and fail closed only for memory (for example, skip the middleware and leave the provider unavailable), or decide that this is the intended fail-closed behavior and document it.

### 6. Fresh-store preparation now fails after the full native install if any configuration write happens during it (Low, confirmed by reading)

- Location: `lifeos_hook_bridge/fresh_store.py:159-160` and `:216-217`.
- Defect: The final check `self._owner(account)!=selected` compares the entire configuration dictionary. The configuration lock is no longer held during the install, so a concurrent revoke, enrollment, or sharing switch changes `clients` or `sharing_enabled`. Preparation then raises "The reviewed source or owner changes during fresh store preparation" after the whole install, and leaves a store that `status` lists as `interrupted`.
- The b37cc07 commit message says "Revocation and the sharing switch can proceed during preparation." That is true, but the in-flight preparation is discarded. This is a fail-safe outcome, not a security defect. No test covers it.
- Race for the wrong installation (focus C): I found none. Every writer of `root`, `principal`, or `accounts` (`cli.py:68`, `memory_import.py:93`, `memory_ownership.py:61`, `profile_backup.py:127`, `profile_backup_recovery.py:56`) holds `installation_lock`, and `prepare` holds `installation_lock` for its whole duration. The writers that can run without that lock (`sharing`, `enroll`, `revoke`, the mount transaction) do not change root, principal, or accounts. The small unlocked window between the final check (line 216) and the review publication (line 223) is therefore harmless.
- Deadlock (focus C): none. `MemoryConfiguration._lock` is a non-reentrant `flock` on a freshly opened descriptor, so nesting would self-deadlock. But the only callers of `_owner` are `prepare` (lines 160, 216) and `status` (lines 141, 152), and none of them holds the configuration lock. `MemoryPreferences.prepare_fresh` and `fresh_status` call `_configuration`, which uses `load()` without the lock. Lock order is installation lock, then configuration lock, everywhere I checked, including the two blocking `installation_lock(wait=True)` sites (`install_source.py:667`, `update_worker.py:227`). Taking the lock inside `_owner` adds little, because `publish` already replaces the file atomically, but it is harmless.

### 7. An unreadable component file makes the whole memory tab return 403 with a misleading message (Low, confirmed by experiment)

- Location: `lifeos_hook_bridge/memory_preferences.py:43` and `:92`; `lifeos_hook_bridge/dashboard/plugin_api.py:122-123`.
- Defect: `source.read_bytes()` sits outside the `try` block. `status()` calls `connection_enrollment_available()` before its own `try`, and that method catches only `MemoryUnavailable`. A component file with mode `0200` (owner write only passes the `0o022` check) raises `PermissionError`. `_memory_action` maps that to HTTP 403 "This dashboard account has no installation owner binding". The optional component thus breaks the mandatory status page. Any other exception raised while executing the component would escape the same way.
- Evidence: `exp5_output.txt`, case 5a.
- Fix direction: convert `OSError` from the read (and import errors) to `MemoryUnavailable` in the loader.

### 8. `revoke` loads the component twice (Negligible, confirmed by reading)

- Location: `lifeos_hook_bridge/memory_preferences.py:276-277`.
- If the component changes between `connection_enrollment_available()` and `self.connections`, revoke raises `MemoryUnavailable` instead of using the fallback. The cost is one failed revocation the operator can retry.

## Areas checked and found sound

- The pinned hash `677cc590...0515` equals the SHA-256 of `optional/lifeos-memory-sharing/memory_sharing.py` at c083037. The component diff against the old in-package module only changes the constructor (keys path now defaults to `~/.ssh/authorized_keys`, override through `keys_file`).
- Directory and file symlinks at the leaf are refused (`lstat` plus `S_ISDIR` and `S_ISREG`). Ownership is checked on both the directory and the file.
- Hardlinks: the checks read inode mode and owner, so a hardlink grants no extra write access. The installer publishes a fresh inode through `os.replace`. POSIX ACLs: a named-user or named-group write entry sets the mask, which shows in the group bits, so `& 0o022` detects it.
- Dashboard package name: with the plugin loaded as `lifeos_memory_settings` (as `plugin_api._memory_preferences` does), the component loads as `lifeos_memory_settings.memory_sharing`, its relative imports resolve to `lifeos_memory_settings.memory_service` and siblings, and `MemoryUnavailable` is the same class that `memory_preferences` catches. A plain `lifeos_hook_bridge` import in the same process uses a separate `sys.modules` key and does not collide (`exp4_output.txt`).
- `sys.modules` caching: every call executes a new module object and returns it, so a later load from a different path cannot hand back an earlier module. The only side effect is that the `except` path can pop another thread's entry, which nothing reads.
- Re-executing the module on each `connections` access has no lock impact: `MemorySharing._lock` is an `flock` on a new descriptor each time, and the configuration lock lives in the cached `memory_service` module.
- Cost: hash plus execution is about 0.2 ms per call with a warm cache (`exp6_timing_output.txt`). `status()` running it on every request is not a performance concern.
- All `MemoryPreferences(...)` call sites were updated for the removed positional `authorized_keys` argument (only `plugin_api.py:115` in production code).
- A disabled grant refuses every request (`memory_service.py:552-555`), so the fallback revocation does cut off data access.
- `register_provider` on a version 1 host is unchanged. With an absent configuration or a valid one with ownership disabled, the new branch does not raise.

## E. Do the new tests test what they claim?

`tests/test_sharing_component.py`:

- `test_loader_refuses_an_altered_linked_or_writable_component`: tests what it names, but only a symlinked directory (not a symlinked file), only a file with mode `0666` (not a group-writable or world-writable directory, and not group-only write), and no bytecode cache or race. Findings 1 and 2 are not covered.
- `test_installer_publishes_private_files_and_removal_deletes_only_its_files`: "deletes only its files" is checked only for a sibling file inside the component directory. It does not cover a symlinked component directory, which is the case where removal deletes a file elsewhere (finding 4). It does not assert that the directory or `__pycache__` is gone.
- `test_plugin_without_the_component_still_disables_an_enrolled_grant`: correct and useful. It does not cover the UI consequence in finding 3.
- `test_runtime_package_contains_no_ssh_key_file_reference` and `test_reviewed_component_hash_matches_the_shipped_component`: correct.
- Environment dependency (plausible, not tested): every sharing test loads the repository copy `optional/lifeos-memory-sharing` through the strict loader. On a checkout with group-writable directories (umask 002 clone), these tests fail with "physical owner files" for an environmental reason. This checkout has mode `755`, so it passes here.

`tests/test_review_fixes_pr3.py`:

- `RequiredMiddlewareRegistrationTests`: correct for versions 1 and 2 with `enabled` forced. Because `MemoryRuntime.enabled` is patched to a constant, the tests cannot see `enabled()` raising (finding 5).
- `FreshStoreLockTests`: correctly shows that the configuration lock is free during `install_prepared_lifeos`. It does not show that `_owner` still sees a consistent read, and it does not cover the effect of a concurrent configuration write on the preparation result (finding 6).

`tests/test_hook_evidence.py::TrackedEvidenceTests`: sound. At c083037, all 1571 ledger artifacts are in `git ls-tree`. At 71987ce, 162 were missing, so the test would have caught the original defect. A worktree `.git` file also satisfies the `.exists()` check.

`tests/test_memory_dashboard_ui.cjs` new test: covers the note and the Revoke button for an enabled connection without the component. It does not cover a disabled connection (finding 3).

`tests/test_memory_dashboard.py`: now runs `install.py --hermes-home <profile>` before loading `plugin_api`. This is the only test that exercises the default component location (`HERMES_HOME/lifeos-memory-sharing`) end to end. That is good coverage.

## What I did not get to

- I did not run any project test suite (as instructed), so I have not confirmed the commit messages' pass counts.
- I did not check how the Hermes plugin manager reacts when `register()` raises after `register_memory_provider` (rollback or partial registration), or under what module name Hermes imports the plugin package. Finding 5's impact statement depends on the first point.
- I did not check whether the Hermes runtime sets `PYTHONDONTWRITEBYTECODE`. If it does, the loader would not create `__pycache__` itself, but a planted cache is still honored, because that flag only stops writing.
- I did not run a live concurrent race for `fresh_store.prepare`. Finding 6 is from reading.
- I reviewed only the test part of c083037. I did not audit the evidence and documentation changes in that commit for accuracy.
- The README's instruction `--hermes-home ~/.hermes` does not mention Hermes profiles where `HERMES_HOME` differs. I did not verify how profiles are laid out on the host.
