# Native note identity needs a corpus check

Date: 2026-10-01. Question: Can governed current fact checks preserve native Cortex identity without a corpus-level constraint?

The first duplicate-ID fixture changes the length of a frontmatter line. Current fact positions then fail their existing digest check. That fixture passes the refusal assertion for the wrong reason. It does not verify duplicate identity.

The corrected fixture copies an equal-length native ID between two registered notes. Current fact positions remain valid. The managed search returns one note, while export returns the other note under the same ID. The native standalone corpus already rejects duplicates. `docs/verification/2026-10-01-memory-staging/duplicate-id-boundary-before.txt` preserves the actual result.

The canonical service now checks unique native IDs. The native managed response validates them again. Staged publication checks the proposed notes against current IDs before it writes files or records. The separate staging failure appears in `staged-id-before.txt`.

Per-record correctness does not establish corpus identity. Both checks belong in the admission boundary. A synthetic fixture must preserve the invariants that are unrelated to its hypothesis; otherwise an earlier refusal can hide the defect under test.
