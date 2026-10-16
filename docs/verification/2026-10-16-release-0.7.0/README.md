# LifeOS 0.7.0 qualification and promotion

Status: qualification in progress. Development `.252` and daily `.253` still select qualified 0.6.0.

The program commit is `30b383f10fbe76ece98295f53f83322e8d3de880`. The complete archive contains 288,186,773 bytes. Its SHA-256 is `873c0519424bfd4bf920f1ca0aef0c418ad7dc3a222fbe9a8f0a25343ac7629a`.

The [package comparison](package-verification.json) verifies both prepared native trees, their 10 Hermes and 25 LifeOS patches, the frozen Python closure, and the stock Hermes program files against the immutable qualified 0.6.0 archive. The reused local cache contains a generated `.bytecode-fingerprint`; it does not establish native equivalence. The immutable archive comparison passes.

All 36 UI tests pass. The [native check](native-sealed-30b383f1.json) passes all 716 tests in 38 files against this exact archive. The live SSH fixture uses only the owned qualification guest at `.214`. Installed candidate acceptance passes. The candidate preserves the selected model and completes a real FlashNext reply. Native HTTP save and recall, actual dashboard restart, complete package reapplication, authenticated rollback, and token revocation pass. Integration completion remains pending. HTTP client acceptance and the three product review rounds remain in the [source verification record](../2026-10-16-http-memory/README.md).

The owned disposable guest is CT110, cloned from the retained stock Hermes snapshot. Production receives the complete package after qualification. No personal data import, reset, provider return, or software removal forms part of this promotion. HTTP access starts disabled on existing servers. Tailscale configuration and external agent enrollment remain separate owner actions.


The [installed update receipt](installed-update-recovery.json) verifies use of the original token and fact after both package transitions. It compares complete HTTP configuration and credential-file bytes across rollback. It does not claim a byte comparison across the preceding update.

Three operator checks require correction during qualification. Temporary preboot service masks correctly prevent first-install preparation. The operator removes only those owned masks after confirming the synthetic guest has no Discord token. The first model invocation inherits a permissive file-creation mask and creates a group-writable cache. The backup policy refuses that directory. The operator uses mask `0077` and corrects the owned synthetic directory to `0700`. Finally, the protected `/health` route returns a sign-in redirect. Actual authenticated MCP recall verifies restart readiness. A subsequent post-update connection refusal occurs during dashboard startup. The replay waits boundedly for the listener and preserves the original credentials. These corrections change test operators, not product policy.
