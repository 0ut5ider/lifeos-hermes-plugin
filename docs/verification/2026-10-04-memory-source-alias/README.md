# Source registry alias protection

Date: 2026-10-04. This unit protects an open SQLite transaction from content paths that hard link to its authoritative registry.

The [original two-path control](before.txt) and [expanded corrected control](corrected-before.txt) use a real independent SQLite process. TELOS, WORK, system documentation, and fact projection reads release the process's lock when the invalid UTF-8 descriptor closes. The independent writer acquires `BEGIN IMMEDIATE` after collection despite the active transaction. Path and diagnostic attestation also allow the alias. The corrected baseline records six failed subtests and two passing parent tests.

The native USER path resolver and system source check now reject inode equality before opening content. The [candidate](candidate.txt) passes two tests and six subtests. Each source refusal keeps the independent writer blocked. Each completed transaction permits that writer to acquire the lock.

The [broader gate](gate.txt) passes 264 tests and 111 subtests in 313.09 seconds. There are no failures, errors, skips, or warnings. It covers native operations, source review, source labels, adoption, diagnostics, prompt collection, both TELOS writers, graph rendering and HTTP, native backup and reconstruction, profile backup and separate recovery, distributed preparation, and footprint contracts. The [command](gate-command.json) records exact inputs and source hashes. This unit changes no native patch file.

The initial expanded test incorrectly nests transaction-opening APIs inside an existing transaction. It blocks on its own flock and is interrupted. The [interrupted output](expanded-before.txt) is retained. The corrected test exercises lower-level source checks and actual source collection within the existing transaction. Its measurement independently establishes the product bug.

Checks do not protect against a hostile process with the same operating-system identity replacing a file between attestation and opening. Memory ownership remains disabled. No active server, configuration, shared memory record, or deployment changes occur.
