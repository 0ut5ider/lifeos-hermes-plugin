# Discord admission after scheduled delivery

On October 16, daily receives a human greeting and refuses it before model execution. The error reports missing verified memory context and unavailable compression lineage. Gateway readiness checks and headless model checks pass before this incident. They do not exercise this foreground lifecycle.

Safe native metadata shows three assistant messages and no user messages in the affected foreground session. Its parent ends with `session_reset`, not compression. The fixed morning operator uses `hermes send`. That path mirrors the delivered notice into the destination session as an assistant message. Hermes derives `is_first_turn` from whether any conversation history exists. One notice therefore makes the first human turn appear resumed. LifeOS has no admission for that session and correctly refuses its history.

The [synthetic reproduction](reproduction.json) uses the actual native session store, delivery mirror, prompt callback, and native memory fixture. The notification-first session refuses. The empty session passes. No production data supplies the reproduction. Adrian confirms a normal real Discord reply after `/new` and a greeting. Lasting memory does not reset.

The fix must preserve the memory admission refusal for unverified history. It must also preserve delivery and mirroring in admitted conversations. A fresh session must not gain unverified history from an outbound notification before its first human turn. No notification may create memory admission on the owner's behalf.

The source fix extends the existing `pre_message_delivery` hook with a mirror purpose and exact destination session. The private-channel policy returns a separate mirror decision. It requires an existing admission for the same author, destination, private audience, and current scope. It compares the session-independent scope signature used by `MemoryRuntime._stamp`. A notification never creates an admission. Ordinary outbound delivery stays available. Native mirroring stays available after foreground admission and after memory ownership returns to Hermes.

The native mirror treats a refused or invalid policy result as a skipped transcript write. It does not resend the notification or report a successful delivery as failed. The existing memory admission and compression recovery checks remain unchanged. All ten Hermes patch groups replay against the frozen stock archive. The replayed mirror matches the tested implementation. The fix adds no patch group and changes no upstream pin.

A characterization assertion initially compares native rows without their persistence metadata. The corrected assertion compares role and content. The corrected baseline then reports five expected failures. A first wider run reports 30 errors because the extracted test source lacks its root YAML dependency. The corrected fixture uses the same archive source and the existing synthetic runtime dependency directory. The completed run passes 116 tests. A separate native run passes 70 tests. Two additional author and provider-return cases pass separately, for 118 unique bridge cases.

The wider run also measures an unclosed failed audience response. A real local HTTP 404 reproduces the open response. The audience client now closes that response before propagating its refusal. The completed run has no resource warnings or unhandled errors. Its asynchronous fixture retains normal slow-callback timing diagnostics.

Daily chat is restored by the owner's native `/new` and greeting. The [recovery receipt](daily-recovery.json) records the supplied screenshot and normal reply. Production still runs the immutable 0.7.0 release. This source fix requires review and a complete qualified patch release before deployment. No manual morning job, substitute Discord message, personal-data import, or lasting-memory reset supplies this evidence.

The [post-recovery native metadata](daily-after.json) confirms a live foreground session with both human and assistant messages. The observer reads role counts and session identifiers only.

The baseline reproduction operator uses the immutable 0.7.0 Hermes source. The regression suite registers the complete private delivery policy and exercises the corrected native mirror.
