# Decode JSON before source admission

Date: 2026-10-04. The StateEvidence compatibility work uses synthetic files and the pinned LifeOS source. The [baseline record](../docs/verification/2026-10-04-memory-state-evidence/before-output.txt) exposes ungoverned source reads and cache publication.

Two additional native controls fail when JSON escapes hide a private delimiter or the first letter of a retired work name. Raw file text contains the escape sequence. The native parser turns that sequence into a string which reaches a source note or work metric. Checking only the raw bytes cannot enforce the same rule on the eventual output.

Admission now parses the JSON and checks its decoded keys and string values. It preserves the original file bytes for native calculations and exact source review. Malformed JSON, nonfinite values, and invalid Unicode do not enter the admitted source map. Exact reviews remain bound to raw content and current retirement state. A review cannot approve decoded private or known retired text.

The first candidate gate passes 14 tests and four subtests. The expanded gate passes 22 tests and 18 subtests. An independent same-date comparison matches all four domain payloads against the pinned original implementation. Publication interruption, source changes, owner changes, registry aliases, and previous-cache recovery pass in the expanded gate. The final gate passes 183 tests and 124 subtests. All 39 native patch files match the distributed preparation.

No external feeds are configured. The source fixtures do not establish live health, activity, work, or finance integrations. The product keeps the cooperative writer boundary and does not defend against hostile same-UID filesystem replacement between the final path check and publication.
