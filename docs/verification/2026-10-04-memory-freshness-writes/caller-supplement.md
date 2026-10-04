# Timestamp and cache callers

Date: 2026-10-04. This supplement records the publication boundaries added after the freshness reader gate.

| Native entry point | Managed effect | Native caller coverage |
| --- | --- | --- |
| `bumpTelosTimestamp` | Render the original file and section timestamp transformation from admitted source text. Publish the fixed source through the journal. | Direct library controls, unknown sections, missing files, current owner context, and native bytes. |
| `bumpContextTimestamp` | Render the original frontmatter transformation. Preserve the review clock. | Direct library controls, default writer identity, fixed system targets, empty and plain sources. |
| `bumpReviewedTimestamp` | Render the original review clock transformation. Preserve the write clock. | Direct library controls, native bytes, retired sources, and current write authority. |
| `stampContextWrite` | Keep the original best-effort report and template provenance change. | Direct library controls, native bytes, denied writes, and repeated provenance changes. |
| `FreshnessCache.writeFreshnessCache` | Render the original constitutional payload. Publish the exact cache artifact through the journal. | Actual CLI write, print, authority, path, interruption, and recovery controls. |
| Timestamp-triggered cache refresh | Keep cache refresh best effort after a successful timestamp operation. Use the same managed cache writer. | Actual timestamp controls and cache field comparison. |

The native patch now includes `FreshnessCache.ts` as file 37. SessionStart registration remains covered by the existing native cache test. That test uses an unmanaged disposable root. It does not establish complete managed SessionStart acceptance.

`InterviewScan.ts`, `InterviewDue.ts`, `StateEvidence.ts`, `MigrateContextFreshness.ts`, derived synchronization, other native publishers, and restricted-context delivery remain separate open boundaries. The migration baseline and scratch renderer work start after this unit. They are not included in its distributed patch or passing gate.
