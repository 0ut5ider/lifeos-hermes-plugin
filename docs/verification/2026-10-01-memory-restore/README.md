# Managed native hot-memory recovery

Date: 2026-10-01. Data is synthetic. Running ownership remains disabled.

## Recovery contract

Managed recovery repairs current registered facts from a native snapshot. It preserves later current facts, reference identifiers, revisions, writers, and provenance. It does not reactivate a forgotten or superseded snapshot entry. Unknown snapshot entries remain excluded. Unknown current facts need adoption review before recovery can proceed.

The owner previews one exact native snapshot. The preview identifies the source bytes, current target bytes, selected category records, installation, and scope. Application compares that signature inside the cooperating publication transaction. A changed source or intervening current write produces a conflict. Retry uses the same operation receipt.

Snapshot and target paths must resolve to their exact permitted physical locations. Snapshot names follow the native timestamp format. Each source has a 256 KiB limit before native parsing. The native lenient hot parser extracts entries. Native validation checks the declared current set. The native writer retains its validation, file lock, caps, shrink guards, snapshots, and audit events. The plugin journals target and audit publication with the operation receipt.

The recovery receipt includes counts and preserved references. It does not quote excluded facts through native eviction details. The original snapshot remains native recovery evidence. Snapshot retention is still the native best-effort ring. This unit does not make that ring a transactionally complete backup.

## Native command behavior

1. Run `bun MemoryRestore.ts list principal` to list permitted snapshots.
2. Run `bun MemoryRestore.ts restore <snapshot-file>` to obtain a preview.
3. Review the recovery counts and excluded snapshot count.
4. Run `bun MemoryRestore.ts restore <snapshot-file> --signature <signature> --request-id <identifier>` to apply that preview.
5. Reuse the request identifier for a retry of the same preview.

`latest principal` produces a preview for the latest permitted snapshot. The preview returns its exact snapshot name. Apply that name explicitly. This prevents a new ring entry from changing the selected snapshot between commands. Without a managed connector, native byte-copy restoration remains unchanged.

## Evidence

- `before.txt`: a native unbound restore republishes a forgotten fact. The seven absent-interface errors are expected before the managed recovery module exists. The standalone byte-copy control passes.
- `after.txt`: nine initial real native cases pass in 18.810 seconds.
- `expanded.txt`: fifteen cases pass in 31.863 seconds. A subprocess exits immediately after actual native publication. The next transaction restores the pre-publication bytes, and retry repairs the current fact.
- `preparation.txt`: ordered distributed source preparation succeeds. The existing LifeOS memory patch now changes 21 files. This unit adds no Hermes patch group.
- `focused.txt`: the distributed recovery gate also runs neighboring curation, native publication, and delegation cases. Its final result is recorded below after completion.

The complete source and derived-reader inventory, staged promotion, restricted prompt and lifecycle cases, ownership setup, coherent backup and restore, and the full release gate remain open. This unit establishes individual current-fact recovery, not complete backup restoration or whole-design activation.

The distributed focused gate passes 66 cases in 148.415 seconds without skips, failures, or errors. This includes 18 recovery cases, both real process-death boundaries, native command preview and apply, and the unchanged neighboring publication, curation, and delegation controls.
