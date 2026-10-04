# Selected profile and native snapshot

Date: 2026-10-04. The [gate](gate.txt) passes 47 tests and 20 subtests without skips, failures, or uncaptured warnings. The [command](command.json) records the environment and tested source hashes. The [completion marker](gate.done) records exit status 0.

The actual Hermes parser exposes `hermes lifeos-backup --scope profile --create DIRECTORY` and `--scope profile --inspect DIRECTORY --signature SIGNATURE`. The command uses the selected profile. It preserves configuration, identity, memories, histories, skills, installed profile files, binary files, empty directories, source permissions, source timestamps, and covered links. Native data retains its private manifest and reviewed signature within the same archive.

Installation and configuration locks precede sorted profile SQLite writer barriers and the native transaction. Database images use the open connections and standalone SQLite format. Collection checks source state twice and preserves the original configuration. Each profile and native collection is bounded to 64 MiB per file, 256 MiB total, and 100,000 source entries. Archive files use mode `0600`; directories use `0700`.

The real-process concurrency control checks the initial SQLite and native file locks. It also starts fresh SQLite processes after native collection and after both profile collections. Every probe receives lock refusal. The waiting native and history writers commit after publication. The archive retains one earlier fact and one earlier history row. The live stores retain both later commits. No model request occurs.

The [physical trace](concurrency-trace.txt) retains the failed direct-descriptor experiment. The waiting writer changes the physical database header and commits while the backup connection serializes its prior image. Direct descriptor closure releases the process's SQLite record locks. The connection-only collector fixes the measured cause. See [SQLite's locking guidance](https://www.sqlite.org/howtocorrupt.html) and the [engineering note](../../../notes/2026-10-04-profile-backup-locks.md).

The [native probe](native-barrier-before.txt) reproduces the same SQLite descriptor defect in native collection. Native collection now also uses its connection without reopening the database. The [alias controls](database-alias-before.txt) require refusal before reading a second pathname for the locked inode. Discovery completes before database locks and refuses repeated database inodes.

The controls also cover database replacement, owner account refusal, unchanged existing archives, changed copy hashes, invalid manifest lists and paths, unknown external links, and a pipe that could block a regular file reader. Covered links must resolve inside the selected profile or native physical data boundary. Backup records link text without following it.

A real subprocess exits with status 73 after the private archive manifest exists and before publication. The parent inspects the remaining stage, verifies the original files, and creates a fresh archive. The interrupted stage remains private and available. Normal failures remove only their unpublished staging directory.

An intermediate run exposes a test-edit mistake: the pipe test accidentally contains the remaining interruption assertions. The corrected fixture keeps the complete interruption test and the separate pipe refusal. The final gate includes both tests.

This archive captures supported selected-profile files and native data. It does not restore the profile, select ownership, start services, or capture program sources and service definitions outside the profile. Concurrent non-SQLite edits require stable source collection. The remaining ownership, service recovery, installation, migration, routing, voice, and combined release gates stay open. No active server changes.
