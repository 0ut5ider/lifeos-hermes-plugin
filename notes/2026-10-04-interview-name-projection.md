# Decode assistant names before interview admission

Date: 2026-10-04. Two [pinned native controls](../docs/verification/2026-10-04-memory-interview-scan/escaped-before-output.txt) show YAML escapes becoming private or retired assistant names in interview prompts. Raw Markdown validation sees escape sequences. The native YAML parser turns them into the displayed name.

The scanner now calculates from declared source snapshots. Its native name renderer uses the admitted identity frontmatter and the native default identity. The bridge checks the decoded name with the raw source text before that identity enters scoring or prompt construction. Managed naming does not borrow ambient settings or configuration overrides. Standalone naming retains the native configuration chain.

The first native candidate is blocked by a Python syntax error. A [direct service probe](../docs/verification/2026-10-04-memory-interview-scan/probe-candidate-output.txt) identifies the missing parenthesis. The corrected candidate passes 11 tests and three subtests.

The [review control](../docs/verification/2026-10-04-memory-interview-scan/review-before-output.txt) finds the same decoding gap in exact source review. Both escaped names pass its raw checks. Source review now includes the decoded native name in admission while keeping the raw source digest unchanged. The shared identity projection now also governs generic identity reads. The final regression gate passes 263 tests and 186 subtests. Six output modes match the pinned native scanner exactly. Sixteen recorded native controls pass, including post-render source, owner, installation, and evidence-availability changes.

All source data in these controls is synthetic. No production source or external data integration changes.
