# Governed native proposal outcomes

Date: 2026-09-30. Status: development operations implemented; native writer interception and automatic approval remain open.

The proposal interface now returns pending, diverted, committed, rejected, conflict, or unknown results. It uses native LifeOS validation, enqueue, scope routing, and acceptance or rejection. Pending proposals do not enter current-fact recall. A fact-write grant does not confer proposal creation or approval. External clients can receive create and review grants but cannot receive approval. Approval verifies the queued row and the target revision before native application.

The native scope classifier reads the installation's real skill, hook, and project registry. The initial symlink-based fixture resolved this registry in the source tree, which made a synthetic project look global. The proposal fixture now copies system tools into its own installation and creates a synthetic project row. The actual scope classifier then diverts its project-specific proposal into the native upgrade store.

Recovery records each exact native upgrade destination before publication. An optional native publication observer gives the isolated worker the final filename. A directory snapshot was rejected because rollback could remove a file that another writer created. The recovery test now confirms that an unrelated file survives the interrupted operation.

Independent review reproduced two additional defects. Eight distinct claims with the same first eight words produced only two upgrade records. The native identifier used a second-resolution timestamp and a truncated slug. It now includes the native claim hash. A dangling state-file symlink also let a native write leave USER_DATA before recovery rejected it. The publication observer now checks the destination with lstat, including dangling links, before registering it. The regression tests reproduce both failures and pass after the fixes.

The development metadata schema is version 3. Earlier metadata versions are rejected. There is no live metadata migration, and no active account uses this schema.

The tool set includes proposing a change, listing pending changes, and accepting or rejecting a referenced change. Proposal edit decisions, applied-elsewhere decisions, automatic approval, native direct writer interception, adopted queue rows, and preferences controls still require implementation. These operations do not yet establish governance of all native proposal writers.

The full plugin suite passes 514 tests with 77 fixture-dependent skips against fresh prepared source trees. Patch-regeneration coverage adds one further test. Native source preparation succeeds. Ownership activation remains disabled, and no server configuration changed.
