# Evidence corrections for pull request 3

Date: 2026-10-05. An [independent evidence review](../../agents/2026-10-05-pr3-evidence-review/pr3-evidence-review.md) reads the paired driver, the ledger, and the October 5 units at commit `71987ce`. The primary agent confirms the findings below before each correction.

| Finding | Confirmation | Correction |
| --- | --- | --- |
| Raw captures for six units are absent from Git. | `.gitignore` excludes `*.jsonl` and `*.log`. 162 ledger artifacts were untracked, and the ledger check failed on a clean export. | The 162 files are now tracked. A new test fails when a ledger artifact is untracked ([before.txt](before.txt)). The ledger check passes on a clean export of the corrected tree. |
| The two clients run different hook programs, and the records do not say so. | 29 hook files differ: 15 in identity text only, 13 in program lines, and one exists only in the prepared tree. | [source-differences.md](../../parity/source-differences.md) records the measurement. Six unit records now link to it. |
| Tool logging summaries hide differences in row content. | The raw rows differ in output fields, in error text, and in one input field. | The tool logging record and both ledger rows now state the differences. The cases remain in the ledger as equal on event, row kind, and command only. |
| One tool logging statement is not observable. | The failure case registers no PostToolUse hook. | The record no longer states that PostToolUse is absent. |

## Findings that remain open

1. The comparison covers selected fields. Files outside the selection are not compared, and duplicate rows collapse in one summary.
2. Several checks cannot fail: the time-context before-state, the model output flag for the failing command, the guard project listing, and the timestamp check over zero rows.
3. The tier route unit maps every tier to one model, so it cannot detect a wrong model route. The relay reports its configured model name.
4. An invalid clock or empty hook output on one side stops a run with an error and records no failed case.
5. The three end-of-turn cases that expect no page read the state without a wait for a late render.
6. Model delivery claims depend on request bodies outside Git.
7. The unit tests do not cover `run_side`, most state readers, or the `collect.py` scripts.
8. Neither check compares hook source digests between the two sides.
