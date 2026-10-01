# Native wiki read validation

2026-10-01, local plugin development. The synthetic collector tests passed, but the pinned documentation probe admitted 2 of 60 native pages. Standalone LifeOS admitted all 60. Collection used 1,443,524 bytes and took less than 0.4 seconds. Transport size and latency did not explain the rejection.

The collector used `sanitizeTypedItemForPersistence` to validate whole documents. That function validates a new fact write. It rejects frontmatter, comments, and content above 65,536 characters. Those rules conflict with ordinary installed Markdown. The [probe data](../docs/verification/2026-10-01-memory-wiki-corpus/documentation-before-probe.json) records each source and rejection reason. Failing tests preserve native comments, horizontal rules, frontmatter, and larger read content while keeping the write limit unchanged.

The read boundary uses the native `CaptureEnvelope.stripPrivateContent` function and the canonical control and Unicode rules. A changed private projection excludes the complete source. The Python collector also verifies exact physical paths, UTF-8, the 256 KiB file limit, the 3 MiB corpus limit, and current retirement rules. This does not change native fact write validation. The shared memory service still returns `integrity_error`; no alternate access path was used.
