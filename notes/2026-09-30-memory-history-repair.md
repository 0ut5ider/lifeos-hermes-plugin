# Memory changes and conversation context

Date: 2026-09-30

Question: Can a complete Hermes turn confirm a native correction or forget operation after its memory admission becomes stale?

The initial native write succeeds in both cases. The actual model endpoint receives two requests, including retrieval of the current fact. The correction replaces the fact. Forgetting removes it from ordinary recall. Hermes then refuses the third request because the memory generation changes. Three retries repeat that refusal, and the final response describes the provider as temporarily unavailable. This is an incorrect explanation of a context policy refusal.

The first test capture also exposes a fixture problem: host retry diagnostics appear on standard output before its JSON report. The corrected fixture captures those diagnostics separately. The structured result still proves the same product failure. Both captures remain in the verification directory.

The implementation uses existing required execution middleware to project chat history before final admission. It preserves the transcript and protocol identifiers. Removed content receives an explicit exclusion label in model input. The current user quote remains available. Only a fact-generation change can refresh admission in this path. Identity, policy, and installed prompt changes continue to refuse retained admission.

This unit does not enable memory ownership on a running installation. Resume, native prompt reconstruction, compression rotation, complete route coverage, and the ownership transaction remain separate gates. Test facts and accounts are synthetic.

## Review findings and measured corrections

The first independent review finds a state publication race. A repair reads the registry before taking the cooperating lock, so a concurrent admission disappears when repair publishes its stale copy. The lost session then passes an ownership-disabled guard because its retained lineage is absent. Rereading and revalidating the registry under the lock preserves both sessions. The unchanged reproduction now refuses the inactive retained session. Its final assertion still expects the original defect, so its exit code alone is not the closure result.

A complete native LoadMemory test exposes another stale source. Hermes appends native recall to the current user message. Exempting that entire message preserves the retired fact in the third model request. Admission now records only the input kind, length, and hash. The request projection preserves the verified original input and filters appended context. Both actual native recall turns pass after this fix, and the transcript remains intact.

The next independent review finds an ordinary compression regression. A generated summary prompt has a user role, but it is not the original human input. Applying the original-input proof rejects benign compression with zero requests. Auxiliary calls now inspect all generated content without the primary quote exception. The unchanged archived child passes both primary and summary-helper controls, with one HTTP request each. The archived parent script cannot regenerate that child because its source substitution no longer matches the expanded admission call. This is a probe fixture error. The retained child remains unchanged and supplies the actual closure evidence.

The second closure finds a missing auxiliary input form. A `memory_review` Responses call sends a retired claim as string input. The generated scan now covers every trusted auxiliary task. Its original probe refuses that call before transport, while the primary quote control still sends one request. A separate real SDK test also demonstrates escaped JSON hiding a claim in top-level instructions. Materialized system content now receives the same recursive decoding check. The primary focused gate passes 71 tests after these changes.
