# Profile backup and descriptor lifetime

Date: 2026-10-04. Role: primary implementation and verification. The selected profile snapshot must preserve Hermes files and committed SQLite history together with native facts. All sources use isolated synthetic accounts.

The first gate has four failures. The stage is private, but `profile` has mode `0755` while `profile/files` has mode `0700`. `mkdir(parents=True, mode=0o700)` does not apply the requested mode to an intermediate parent. Explicit creation of `profile` fixes the refusal. The first expanded gate passes 18 tests.

A real file-replacement trace then shows another defect. The open connection serializes the former database after its pathname names a replacement. Physical device and inode checks refuse this snapshot. Discovery refuses duplicate database inodes and completes before opening writer barriers.

The concurrency control initially passes, then fails in the combined gate. The two inventories have identical committed database images but different database and root timestamps. The physical trace shows the raw header transaction counter changing from 2 to 3. The waiting SQLite writer commits while the backup connection still believes its transaction is active.

Direct file collection opens and closes another descriptor for the locked database. POSIX close semantics release the process's record locks for that inode. SQLite documents this precise backup and file-type inspection trap in its [corruption guidance](https://www.sqlite.org/howtocorrupt.html). The collector now uses the SQLite connection to serialize the database and uses `lstat` for physical metadata. It never opens the locked database directly during collection.

Eight subsequent concurrency runs pass. Stronger controls start fresh SQLite probe processes after each collection. Each probe must receive `database is locked`. The actual native writer also observes the native file lock before waiting. Both later writes commit after archive publication, while the archive retains the earlier native fact and history. The combined gate then passes 36 tests and 13 subtests.

The source inventories remain strict. Content, permissions, file metadata, link destinations, and database physical identity must remain stable. The correction does not ignore timestamp changes or add retries. Native backup uses a separate cooperating file lock, but its direct database read needs the same SQLite descriptor correction. A focused probe covers that next boundary.

The native SQLite probe also reproduces the descriptor problem. Its cooperating file lock still blocks normal native writers, but the SQLite record lock disappears. Native database collection now also uses the connection and filesystem metadata without a direct descriptor read. The combined control checks both barriers.

No active server configuration, source facts, services, sharing, or ownership change. Profile snapshots preserve original files; they do not start a recovered service or restore program sources outside the profile. Ownership activation and service recovery remain separate release gates.

The final gate passes 47 tests and 20 subtests in 76.31 seconds. It includes the actual selected-profile CLI, adjacent native backup/recovery commands, plugin footprint, and installed commands. A test-edit mistake temporarily placed interruption assertions inside the pipe refusal case. The final gate restores both complete cases. Hard-link controls also refuse alias reads before a second pathname can close a descriptor for the locked inode.
