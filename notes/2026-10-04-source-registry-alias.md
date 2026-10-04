# Source aliases can release a database lock

Date: 2026-10-04. A synthetic Markdown hard link to the active SQLite registry releases the current process's database locks when a failed UTF-8 read closes its file descriptor. An independent SQLite writer reports `database is locked` before collection, then acquires `BEGIN IMMEDIATE` after collection. This occurs for TELOS, WORK, system documentation, and a registered-fact source projection. Invalid text refusal alone does not preserve transaction isolation.

The corrected characterization records six failed subtests. Three Markdown reads and one fact projection release the lock. The path and diagnostic attestation controls also permit the alias. The candidate rejects inode equality before opening content, in the native USER path resolver and the system source check. Two tests and six subtests pass. The independent writer remains blocked until the real transaction closes, then acquires the database lock.

The first expanded fixture nests transaction-opening APIs inside an existing transaction and blocks on its own flock. That run is interrupted. The corrected fixture uses the source path helpers and actual reads with the existing transaction. Its results establish the source bug independently from that fixture error. The baseline and candidate use synthetic disposable data only. No shared memory records or active servers are accessed.

The broader gate passes 264 tests and 111 subtests in 313.09 seconds, without failures, errors, skips, or warnings. It includes coherent backup, separate recovery, adoption, current readers, graph HTTP, and both TELOS derivative writers. No native patch changes are required.
