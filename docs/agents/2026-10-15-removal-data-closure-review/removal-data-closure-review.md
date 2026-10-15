# Removal data closure review

Date: 2026-10-15

Role: Independent read-only reviewer.

Question: Do the removal-only data barrier and symmetric protected-path checks close the previous findings without weakening normal memory admission?

Model: gpt-6.1-sol, high reasoning effort.

Reviewed commit: `8d041bba`, feature/memory-portability.

Disposition: CLEAR for the two previous publication-core findings and the adjacent data-barrier boundaries tested here. No new measured actionable issue remains in this focused scope.

The untracked removal ownership and preparation implementations are outside this review. Full preparation, manager actions, dashboard controls, standalone launch, installed acceptance, and final release proof remain pending.

## Previous findings and measured responses

| Previous finding | Current response | Independent result |
| --- | --- | --- |
| Actual MemorySystem.ts deletion prevents rollback. | Removal uses a data-only barrier that does not need installed native tools. | The original probe now rolls back successfully. Gateway and dashboard become active. Pulse remains stopped. |
| A late interrupted removal cannot resume after tool deletion. | Apply recovery uses the same retained-data barrier. | The original late-interruption probe resumes to verification_required. |
| The core accepts a directory above the protected native store. | Target validation rejects both descendants and ancestors of protected paths. | The original .config/LIFEOS ancestor probe refuses admission. |

The copied original probes remain unchanged apart from their artifact directory. They use a private physical copy of the actual native tools, exact prepared program entries, owner plan signatures, and actual service fixtures.

## Independent tests

The current data-barrier tests, publication tests, and three original probes pass all 10 tests in 23.319 seconds. These include the existing actual process-exit test after the first software publication, as well as normal rollback preserving later built-in memory.

Three additional data-barrier controls also pass:

1. An actual child process cannot acquire the native writer lock while the removal barrier holds it. The child then completes an actual native transaction after release.
2. Replacing the registry with a different inode containing the same bytes causes the barrier to refuse. The registry content remains unchanged.
3. A missing registry causes refusal. The barrier does not create a database.

The writer test first records the child attempting its native transaction. It is then strengthened and rerun with an explicit nonblocking LOCK_EX attempt against the actual lock file. That attempt must fail before the child enters the normal native transaction. The stronger version passes independently in review-removal-data-lock-proof.

The three adjacent controls pass in 1.467 seconds. The runner receipts record complete wall time separately from unittest execution time.

## Data barrier review

The normal NativeMemory._boundary still calls retained-link validation and then requires MemorySystem.ts. The refactor extracts the unchanged data checks into _data_boundary. It does not make ordinary memory operations work without native tools. The supplied test verifies normal _transaction still refuses after tools disappear.

The removal-only barrier requires an existing registry within the retained native USER boundary. It opens a private regular file with one hard link and records its device, inode, permissions, owner, and link count. It uses the existing MemoryTransaction lock and refuses a pending native publication journal.

The SQLite connection uses mode=rw and BEGIN IMMEDIATE. It then enables query_only and requires exact schema version 4. The barrier does not call schema migration or native publication recovery. It rolls the connection back when it exits. The supplied controls verify a content DELETE fails, database bytes remain unchanged, an unknown schema refuses without migration, a pending journal remains unchanged, and a replaced data link refuses.

Physical registry identity is checked before the caller receives the connection and after successful verification. The additional same-bytes replacement control confirms that content equality alone cannot satisfy this identity requirement.

The process and filesystem tests do not simulate power loss. They verify program-level admission, data retention, operating-system writer exclusion, and actual SQLite behavior. They do not establish storage hardware flush guarantees.

## Protected paths

The core now tests both containment directions for native USER data, its native aliases, built-in memory, SOUL.md, recovery sources, and the supported workspace paths. The original unsafe ancestor refuses before application. Legitimate selected software files still publish and restore in the passing core tests.

This guard supplements exact reviewed program entries. It does not replace the pending preparer's qualified software inventory or the authenticated owner grant.

## Method and limits

The reviewer changes no product files, commits nothing, and pushes nothing. The review accesses no remote hosts, personal records, memory tools, or journal tools.

All fixture data is synthetic. Tests use actual native data files, SQLite connections, operating-system locks, child processes, ProgramTransaction preparation, and user-systemd fixtures. Service tests use the existing serialization lock. No database, filesystem, or service manager is replaced with a mock.

The review does not read or evaluate the new untracked ownership and preparation files. The primary agent continues that implementation separately. The clear result applies to the captured committed core and its tested boundaries.

## Source and raw evidence

source-hashes.json records six committed source and test files. source/ preserves their exact bytes from 8d041bba. test-source-hashes.json records the copied previous probes and the additional controls. Every runner label has raw stdout, stderr, a JSON receipt, and a completion marker beside this report.

| File | SHA-256 |
| --- | --- |
| removal_publication.py | 01fa3c3eafd36f277e0c7ab274de196ca2463ddcc6bbbd58d2c4462baa991c6f |
| removal_data.py | 18265a2a3683e93c950f838c0ee644de881d50113c79c0f81f087e1a5f9250e7 |
| memory_access.py | b4a39d8d98f7476eafaca988791b03f30adf63df356e1f803c113d1213f966ad |
| memory_transaction.py | 0d87bd80db6979dfdf5965430bdf97229d80d7dc332f4c5659bdd7fb25e98e88 |
| test_removal_publication.py | 5db5c934d7194d0f5513c3da950ac9343ce42b10229ec3d351429ba93b8e65e6 |
| test_removal_data_barrier.py | 1cf1eaa24e7d428212d0c0dd69577456e08fab19b73d56369f2fd342ace8ed6a |
