# Current owner capability telemetry baseline

Date: 2026-10-08. The prepared operational-history-second candidate still exposes the raw capability reader.

Six tests report 17 failed assertions. Anonymous requests read labels. Private and retired rows affect aggregate counts. Revocation, connector loss, redirected paths, unsupported methods, and unknown selectors still reach the raw reader. Populated owner output matches the independent original native control except for the required missing no-store header. The generated timestamp changes per request and receives an independent format check.

The native reader supports 60-, 360-, and 1,440-minute windows. Their activity byte windows are 4,000,000, 10,000,000, and 20,000,000 bytes. Subagent history uses a 500,000-byte tail. The dense comparison contains more than three MiB of event rows and passes its aggregation characterization before any correction. The governed implementation must preserve these byte windows and complete counts. A final-record slice or one transport-sized source would change them.

The frontend CapabilityStrip requests all three selected windows. Unknown ownership selectors and duplicate window parameters must refuse access. The candidate must continue to check decoded previews and labels, exact source identity, and current owner authority. The baseline has no managed acceptance. The following candidate adds governed admission.


## Candidate behavior and measured limits

The candidate uses anonymous private snapshots and fixed native byte windows. It validates decoded rows in bounded batches. Native aggregation retains record order and complete permitted counts. It rechecks source bytes, inode identity, missing-file creation, and current owner authority after aggregation. Complete final JSON records without a newline preserve native behavior. A torn final UTF-8 record stays incomplete until its remaining bytes arrive.

The first large-window gate exposes a transport deadline defect. The synthetic activity source contains 25,476,000 bytes. The 60- and 360-minute views return 200. The 1,440-minute view returns 503 after 8.118 seconds. The retained observation confirms that direct owner HTTP returns 200 in 8.729 seconds, while the shared relay times out after 8.013 seconds. The candidate gives only the four declared capability targets a 30-second HTTP deadline. Other memory targets keep their existing deadline.

The second large-window gate passes both cases. The 60-, 360-, and 1,440-minute views return 200 in 2.022, 4.372, and 8.503 seconds. Every field except the separately validated generated timestamp matches the independent original native control.

The native synchronous relay also blocks other dashboard requests. The concurrent-request baseline takes 8.704 seconds to return an anonymous refusal while telemetry runs. The asynchronous capability relay returns that refusal in 0.089 seconds. The telemetry read also returns 200. Both failed observations remain in this directory.

The corrected candidate is `capabilities-second`. The dashboard build passes. All 446 combined tests pass in 636.859 seconds with warnings treated as errors and no skips. The combined gate includes the strict native frontend TypeScript check. The build retains the existing workspace-root and ambiguous duration utility warnings. The retained source identity binds the prepared native file, plugin programs, tests, and both patch copies. Dependency selection uses existing packages after exact manifest and lockfile comparisons. No installed application or private-channel acceptance occurs in this unit.
