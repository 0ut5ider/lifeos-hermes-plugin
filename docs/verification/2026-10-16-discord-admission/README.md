# Discord admission after scheduled delivery

On October 16, daily receives a human greeting and refuses it before model execution. The error reports missing verified memory context and unavailable compression lineage. Gateway readiness checks and headless model checks pass before this incident. They do not exercise this foreground lifecycle.

Safe native metadata shows three assistant messages and no user messages in the affected foreground session. Its parent ends with `session_reset`, not compression. The fixed morning operator uses `hermes send`. That path mirrors the delivered notice into the destination session as an assistant message. Hermes derives `is_first_turn` from whether any conversation history exists. One notice therefore makes the first human turn appear resumed. LifeOS has no admission for that session and correctly refuses its history.

The [synthetic reproduction](reproduction.json) uses the actual native session store, delivery mirror, prompt callback, and native memory fixture. The notification-first session refuses. The empty session passes. No production data supplies the reproduction. Adrian confirms a normal real Discord reply after `/new` and a greeting. Lasting memory does not reset.

The fix must preserve the memory admission refusal for unverified history. It must also preserve delivery and mirroring in admitted conversations. A fresh session must not gain unverified history from an outbound notification before its first human turn. No notification may create memory admission on the owner's behalf.

The source fix extends the existing `pre_message_delivery` hook with a mirror purpose and exact destination session. The private-channel policy returns a separate mirror decision. It requires an existing admission for the same author, destination, private audience, and current scope. It compares the session-independent scope signature used by `MemoryRuntime._stamp`. A notification never creates an admission. Ordinary outbound delivery stays available. Native mirroring stays available after foreground admission and after memory ownership returns to Hermes.

The native mirror treats a refused or invalid policy result as a skipped transcript write. It does not resend the notification or report a successful delivery as failed. The existing memory admission and compression recovery checks remain unchanged. All ten Hermes patch groups replay against the frozen stock archive. The replayed mirror matches the tested implementation. The fix adds no patch group and changes no upstream pin.

A characterization assertion initially compares native rows without their persistence metadata. The corrected assertion compares role and content. The corrected baseline then reports five expected failures. A first wider run reports 30 errors because the extracted test source lacks its root YAML dependency. The corrected fixture uses the same archive source and the existing synthetic runtime dependency directory. The completed run passes 116 tests. A separate native run passes 70 tests. Two additional author and provider-return cases pass separately, for 118 unique bridge cases.

The wider run also measures an unclosed failed audience response. A real local HTTP 404 reproduces the open response. The audience client now closes that response before propagating its refusal. The completed run has no resource warnings or unhandled errors. Its asynchronous fixture retains normal slow-callback timing diagnostics.

Daily chat is restored by the owner's native `/new` and greeting. The [recovery receipt](daily-recovery.json) records the supplied screenshot and normal reply. At that source checkpoint, production still runs the immutable 0.7.0 release. The source fix then requires review and a complete qualified patch release before deployment. No manual morning job, substitute Discord message, personal-data import, or lasting-memory reset supplies this evidence.

The [post-recovery native metadata](daily-after.json) confirms a live foreground session with both human and assistant messages. The observer reads role counts and session identifiers only.

The baseline reproduction operator uses the immutable 0.7.0 Hermes source. The regression suite registers the complete private delivery policy and exercises the corrected native mirror.

## Independent review corrections

Claude Opus 5.5 reviews PR34 at `3634f58b`. The [round 1 report](../../agents/2026-10-16-pr34-opus-review-round-1/pr34-opus-review-round-1.md) identifies one medium regression and three low findings. The primary agent independently reproduces all four destination and ownership failures. The permanent regression run reports five expected failures, including patch assignment. The initial callback-thread test passes on the synchronous caller because Hermes already executes bounded hooks on a worker. That assertion does not measure gateway loop progress.

The mirror-purpose policy now preserves standard Hermes mirroring when memory configuration is absent or ownership is returned. Invalid configuration still refuses. An admitted direct message does not require a guild-channel binding. Its exact stored session, current owner account, private audience, destination, and scope must match. A bound channel retains current Discord audience verification. Ordinary delivery keeps its original channel gate.

The patch generator owns `gateway/mirror.py` and `gateway/platforms/webhook.py`. Regeneration from the prepared source includes both changes. Other patch bodies match; their index abbreviations differ under the local Git configuration. Only the session lifecycle patch is replaced. The webhook caller awaits its synchronous mirror through `asyncio.to_thread`. A local HTTP heartbeat test measures gateway loop progress while mirror permission lookup waits. A real send-tool case resolves the current gateway session without an explicit session identifier and verifies refusal before admission and mirroring afterward.

The focused correction gate passes 23 tests, including native patch regeneration and full replay. Version 0.7.1 is the selected patch-release source. Independent follow-up review, exact-package qualification, publication, and server updates remain required at that correction checkpoint. The servers then run 0.7.0.

The broader primary correction run passes 138 tests. Its initial webhook thread assertion passes before the caller change and therefore cannot establish responsiveness. The final heartbeat assertion deliberately delays the first audience request after actual HTTP delivery. The isolated synchronous baseline cannot advance the loop within the one-second window and reports the expected failure. The corrected caller advances the heartbeat and passes. An earlier heartbeat probe waits on a request count that includes the native forum-type lookup and times out; the corrected probe selects requests after actual delivery. This changes the measurement, not product policy.

The expanded native gate passes 177 tests across mirror, send-tool, cron-origin, and all webhook modules. The final heartbeat test passes separately after its measurement correction. These are source-fixture checks. The exact 0.7.1 archive and installed acceptance remain separate gates at that checkpoint.

## Review completion

The [second Claude Opus 5.5 review](../../agents/2026-10-16-pr34-opus-review-round-2/pr34-opus-review-round-2.md) clears `3cfddbfc`. It independently verifies all four corrections, repeats the heartbeat check five times, and confirms all 95 patched paths after replay. The primary repeats its probe module: 26 cases pass, including the eight added checks. The runtime and tests remain unchanged after this review. Exact 0.7.1 package qualification, publication, and both managed server updates now pass. The [release and deployment record](../2026-10-16-release-0.7.1/README.md) binds the qualified archive, live checks, preserved configuration, and explicit observation limits. PR34 is merged. Development and daily run the same 0.7.1 package.
