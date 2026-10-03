# Governed native proposal outcomes

Date: 2026-09-30. Status: governed native proposal decisions and automatic review are implemented and independently reviewed. Ownership activation remains disabled.

The proposal interface now returns pending, diverted, committed, rejected, conflict, or unknown results. It uses native LifeOS validation, enqueue, scope routing, and acceptance or rejection. Pending proposals do not enter current-fact recall. A fact-write grant does not confer proposal creation or approval. External clients can receive create and review grants but cannot receive approval. Approval verifies the queued row and the target revision before native application.

The native scope classifier reads the installation's real skill, hook, and project registry. The initial symlink-based fixture resolved this registry in the source tree, which made a synthetic project look global. The proposal fixture now copies system tools into its own installation and creates a synthetic project row. The actual scope classifier then diverts its project-specific proposal into the native upgrade store.

Recovery records each exact native upgrade destination before publication. An optional native publication observer gives the isolated worker the final filename. A directory snapshot was rejected because rollback could remove a file that another writer created. The recovery test now confirms that an unrelated file survives the interrupted operation.

Independent review reproduced two additional defects. Eight distinct claims with the same first eight words produced only two upgrade records. The native identifier used a second-resolution timestamp and a truncated slug. It now includes the native claim hash. A dangling state-file symlink also let a native write leave USER_DATA before recovery rejected it. The publication observer now checks the destination with lstat, including dangling links, before registering it. The regression tests reproduce both failures and pass after the fixes.

The development metadata schema is version 3. Earlier metadata versions are rejected. There is no live metadata migration, and no active account uses this schema.

The tool set includes proposing a change, listing pending changes, and accepting, rejecting, editing, or recording a change as applied elsewhere. Native proposal consumers use the same decisions and metadata. Automatic application requires its own grant and the native confidence threshold. Raw native queue and target writers refuse when a connector is present. Standalone behavior remains available only when the connector is absent. Adopted queue rows remain open. The preferences page now exposes pending native rows and all four manual decisions.

Independent review found that a dangling connector link enabled standalone fallback. Presence checks now use lstat and reject the malformed connector. Resolution notes receive native text validation. Persistent decision receipts contain only metadata; native responses read proposal text from the authoritative queue after publication. Accept, edit, and automatic application invalidate retained identity context. Rejection and applied-elsewhere decisions leave unchanged context usable.

The latest full plugin suite passes 527 tests with 77 fixture-dependent skips against fresh prepared source trees. The focused independent closure passes 48 tests. The primary agent also reruns the native and context state matrices. These results cover the tested proposal paths, not complete memory activation or the full release gate. Ownership activation remains disabled, and no server configuration changed.
