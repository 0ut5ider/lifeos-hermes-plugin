# Move patch file hooks

Date: 2026-09-27

The bridge's V4A test used `*** Move to: destination`, but the Hermes patch parser accepts `*** Move File: source -> destination`. Hermes's own file tool tests use the latter form. With that valid header, the bridge skipped both move paths, so LifeOS Edit hooks and permission checks did not see them.

The test now uses Hermes's real move header. It failed because the bridge sent only the delete path. A second test showed that the bridge resolved a deleted symlink to its content target, while Hermes deletes the directory entry. Both tests passed after the adapter recognized the move header and used Hermes's entry path resolver for delete and move targets.

On `.212`, a synthetic move into a temporary invalid LifeOS knowledge note produced two native Edit hook inputs, one for the source and one for the destination. The installed `KnowledgeWriteGuard` returned its off-schema advisory for the destination. The probe did not execute the move. The full local suite passed 79 tests with five optional native tests skipped.
