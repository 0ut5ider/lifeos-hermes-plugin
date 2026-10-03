# Native memory recovery findings

Date: 2026-09-30.

The first foundation passed 14 tests. Independent synthetic probes found five correction and reference defects. Further probes exposed UTF-16 length differences, title collisions, and incomplete section identity. Corrections now validate all native fields before publication. Hot facts have one active reference. Archive references identify the complete generated section.

A rollback journal alone did not prevent lost writes. Killing Python released its file lock while a Bun child could still publish. The surviving child overwrote a later acknowledged fact. The native subprocess now inherits the lock descriptor. Recovery waits for that process to exit before restoring the unfinished publication or admitting another writer.

The journal must exist before the operation reservation commits. Otherwise a crash can leave an unknown result without recovery data. The journal also uses validated native routing. Native files are flushed before the result commits. Temporary private recovery copies are removed after the operation completes. Native audit copies remain retained history.

The 28-test foundation and independent cache probe pass. These results cover process interruptions, not power loss. They govern cooperating access-layer callers. Direct native writers must delegate to the same boundary before memory ownership can change.
