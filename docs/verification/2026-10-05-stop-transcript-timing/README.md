# Stop transcript timing

Date: 2026-10-05. A paired run of the native StopGates hook found a bridge defect. Under Hermes, the format gate never saw the final answer. Under Claude Code, it saw the answer and recorded a finding.

## Measurement

A Claude Code 2.1.272 Stop hook in the development container reads its transcript at 0, 50, 150, 500, and 1,000 ms after it starts. Five runs give the same result ([native-probe.txt](native-probe.txt)):

| Delay | Final answer in the transcript |
| --- | --- |
| 0 ms | No |
| 50 ms | No |
| 150 ms | Yes |
| 500 ms | Yes |
| 1,000 ms | Yes |

Claude Code therefore adds the candidate answer while its Stop hooks run. LifeOS Stop gates call `parseTranscriptFromInput`, which waits 150 ms before it reads the transcript. The September 28 probe read the transcript at once and found no candidate. That result is correct for an immediate read but missed the later write.

## Defect and correction

The bridge appended the candidate after all Stop hooks finished. Every LifeOS gate that reads the final answer from the transcript then found no answer and passed silently. This affects the format, verification, ISA close, ISA fold, ISA structure, deployment registration, and writing gates in StopGates.

The bridge now starts a timer when the Stop hooks start and appends the candidate after 100 ms. A hook that reads at once still sees no candidate, as in Claude Code. A hook that waits 150 ms sees it. When the hooks finish earlier, the bridge cancels the timer and appends the row once. A blocked candidate stays in the transcript, as before.

The new regression fails before the correction ([before.txt](before.txt)): a hook that reads after 300 ms found no answer. The bridge, provider, and Stop effort suites pass 191 tests with one optional skip ([after.txt](after.txt)). The earlier ordering regression still passes.

## Limits

The 100 ms delay is an emulation of a measured race. A native hook that reads the transcript between 50 and 150 ms can see either state. A paired StopGates case on the corrected plugin is the next check.
