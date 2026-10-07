# Native review admission recovery

Date: 2026-10-07. Role: primary engineer. Model: GPT-6.1. Question: can an interrupted Stop trigger duplicate an already started memory review?

The actual Bun rename control kills MemoryReviewFire after its detached reviewer starts, before the global cadence stamp replaces its destination. Retrying the same session starts a second reviewer. The retained failing control records two reviewer-fire rows. The test uses an empty actual transcript, so its reviewers take the native no-exchanges branch without model inference.

The admission now replaces the global cadence stamp before starting the reviewer. Both cadence files use the existing atomic writer with mode 0600. The same kill-and-retry control passes with one reviewer start. A process killed after admission but before spawn can miss a review until the cadence permits another attempt. The native failure policy already consumes cadence after an unavailable reviewer. This change applies that policy to interrupted admission. It does not guarantee exactly-once network inference across arbitrary external failures.

A separate enabled control runs eight concurrent admitted sessions through the real bridge and private model. It requires one detached review, pending proposals, no automatic application, and no additional fire after eight immediate repeated Stops. The authentication-failure control receives an actual HTTP 401 and requires an absent proposal queue and unchanged target.
