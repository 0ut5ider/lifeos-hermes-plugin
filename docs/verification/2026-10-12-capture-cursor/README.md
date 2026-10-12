# Conduit cursor correction

Date: 2026-10-12. This correction completes the authorized release workflow.

Daily installation and authenticated acceptance pass on version 0.3.0. Capture remains blocked after synthetic memory cleanup. A governed metadata diagnostic identifies 12 processed work events and six pending events. One processed event contains unsafe retained text. No pending event contains private or retired text. Two pending events still predate the retirement cutoff and require explicit review.

The native adapter ignores string timestamps at or before its stored cursor. The bridge validates the complete ledger and copies its raw bytes into native scratch. Three of six initial native tests fail because the complete fold refuses processed unsafe text. Three privacy characterization cases pass.

The correction selects the native pending rows before admission and copies only admitted rows into scratch. It preserves raw ledger fingerprints before execution, publication, and response delivery. Timestamp comparison uses JavaScript UTF-16 order. Missing or unrecognized timestamps retain strict admission.

The pending review target is `LIFEOS/MEMORY/STATE/work-events.jsonl#conduit-pending`. Review includes only pending rows and binds the cursor, complete ledger hash, and retirement state. It cannot approve the full ledger for another reader. Private and decoded retired pending text remains refused. Three initial review tests fail because the selector is unavailable before implementation.

The first neighboring gate passes all 68 selected cases. The retirement test initially uses a pending timestamp that also requires review; its corrected fixture gives new work a timestamp after retirement. A following gate adds large-ledger availability checks. Native source pins and all 36 patches remain unchanged. Published 0.3.0 assets remain immutable. Version 0.3.1 stages and verifies the correction before daily promotion.

The final neighboring gate passes all 70 cases, including large-ledger availability after a stale small-view approval. The earlier two large-work fixtures exceed the per-event 256 KiB limit and fail as intended by that limit; corrected fixtures use three individually bounded rows. No limit changes. Eleven new capture cases cover selected-row input, explicit pending approval, metadata binding, private pending refusal, and concurrency. Current-admission diagnostics confirm two pending events require review because of age.

The frozen 0.3.1 package passes all 552 combined integration cases. Both native manifest hashes and the morning operator hash equal the qualified 0.3.0 artifacts. Installed development acceptance verifies 202 plugin files, 869 native files, and 16,525 Hermes files. The actual model returns `D252-RELEASE-031-PASS`. All three services are active with zero restarts. Selection preserves 141 data and credential files and makes no native program change.
