# Completion-state admission failure is a source conflict

Date: 2026-10-04. InterviewDue publication uses the existing native memory journal. The journal captures previous completion bytes before the native renderer runs.

An actual-render control writes a later completion edit that exceeds the 256 KiB source limit. The first candidate refuses the operation, but leaves an unknown receipt. Recovery then restores the previous completion bytes and removes the later edit. The [failing control](../docs/verification/2026-10-04-memory-interview-due/source-conflict-before-output.txt) records this loss. The verdict-cache control preserves the later completion edit because that transaction journals only the cache.

The post-render source check now converts changed admission into a conflict receipt. The journal can finish that refused operation without treating the later source as an incomplete plugin write. Source content changes, private markup, size-limit changes, and owner revocation all stop publication. Genuine process termination after publication still restores the previous artifact.

The [expanded gate](../docs/verification/2026-10-04-memory-interview-due/expanded-output.txt) passes 16 tests and ten subtests after the correction. It preserves the later completion edit in all six source-change combinations. This repeats the timestamp publication lesson: refusal alone does not prove preservation. A test must reopen the journal and examine the source after recovery.

A subsequent control starts with completion state already excluded by private markup. Comparing only admitted sources misses a later edit because both admitted maps remain empty. The publication check now also compares a digest of the raw source bytes and file time. That case fails before the correction and passes in the final 93-test, 55-subtest gate. The corrected recorder captures all 19 native cases.
