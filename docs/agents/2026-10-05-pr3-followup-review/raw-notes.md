# Raw notes: PR 3 follow-up review (2026-10-05)

## Setup
- Export: `git archive c083037 lifeos_hook_bridge optional | tar -x -C /tmp/pr3review/src`
- Python 3.14.7, umask 0022 on this machine (experiments set umask 002 where noted).
- Repository modes: optional/ 755, optional/lifeos-memory-sharing 755, memory_sharing.py 644, __pycache__ 755 (gitignored by `.gitignore:1:__pycache__/`).
- Hash check: `git show c083037:optional/lifeos-memory-sharing/memory_sharing.py | sha256sum` = 677cc5909520029dba91009161d615f5f699286f8d2b96f9e80cbd9a28e70515, equals SHARING_COMPONENT_SHA256.

## Lock inventory (configuration._lock and installation_lock), c083037
- cli.py:68 installation_lock, configuration._lock
- memory_import.py:93 installation_lock, configuration._lock
- memory_ownership.py:61 installation_lock(lease), configuration._lock
- profile_backup.py:127 installation_lock(lease), configuration._lock
- profile_backup_recovery.py:56 installation_lock, configuration._lock (rebinds root)
- mount_transaction.py:382 configuration._lock inside its own _lock
- install_source.py:667 and update_worker.py:227 installation_lock(wait=True), outermost
- fresh_store.py:96 configuration._lock inside _owner; callers prepare (160, 216, under installation_lock) and status (141, 152, no lock)
- MemoryConfiguration._lock: os.open + flock(LOCK_EX) on a new descriptor, not reentrant.

## Ledger check
- docs/parity/handler-effects.json artifacts: dict, 1571 entries.
- Untracked at c083037: 0. Untracked at 71987ce: 162.

## Experiment outputs
See exp1_output.txt to exp6_timing_output.txt. Summary:
- exp1: unchecked-hash pyc PLANTED; timestamp pyc PLANTED; __pycache__ created 0o775 under umask 002.
- exp2: directory swap after hash, SWAPPED CODE RAN; parent 0o777 accepted.
- exp3: install refuses symlinked dir (SystemExit), dangling symlink FileExistsError, replaces symlinked file without write-through; remove deletes memory_sharing.py through a symlinked directory; remove leaves dir plus __pycache__ pyc.
- exp4: dashboard package name loads and resolves relative imports correctly.
- exp5: unreadable component makes status() raise PermissionError; register_provider on version 2 raises for 0644 config and truncated JSON with ownership disabled.
- exp6: about 0.2 ms per load_sharing_component call.
