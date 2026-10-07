# Migration output contains both source and backup bytes

Date: 2026-10-04. The migration candidate passes its ordinary source, authority, backup, and interruption controls. Seven synthetic context files then test the supported file-size boundary. Each file contains 245,761 bytes, below the 262,144-byte per-file limit. Their combined source size is 1,720,327 bytes.

The actual native renderer returns success and 14 publications. Its serialized result contains 3,447,548 bytes. The bridge checks that result against the 3,145,728-byte input corpus limit and refuses it. The publication list contains both new source bytes and original-byte backups, so this limit incorrectly rejects supported input.

The renderer limit now follows twice the serialized admitted-source size plus the existing corpus allowance for reports and metadata. The caller's console result keeps its separate corpus bound before publication. Source and artifact file limits remain in effect. The same actual-render probe now returns a committed receipt with all 14 artifacts. The final test also checks UTF-8 bodies and complete original-byte backups.

Evidence: [size failure](../docs/verification/2026-10-04-memory-freshness-migration/large-before-output.txt), [actual native sizes and refusal](../docs/verification/2026-10-04-memory-freshness-migration/large-measurement-before.json), and [committed correction](../docs/verification/2026-10-04-memory-freshness-migration/large-measurement-after.json). Production remains unchanged.
