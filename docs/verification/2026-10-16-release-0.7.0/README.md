# LifeOS 0.7.0 qualification and promotion

Status: qualified and [published](https://github.com/0ut5ider/lifeos-hermes-plugin/releases/tag/v0.7.0). Production promotion remains in progress. Development `.252` and daily `.253` still select qualified 0.6.0.

The program commit is `30b383f10fbe76ece98295f53f83322e8d3de880`. The complete archive contains 288,186,773 bytes. Its SHA-256 is `873c0519424bfd4bf920f1ca0aef0c418ad7dc3a222fbe9a8f0a25343ac7629a`.

The [package comparison](package-verification.json) verifies both prepared native trees, their 10 Hermes and 25 LifeOS patches, the frozen Python closure, and the stock Hermes program files against the immutable qualified 0.6.0 archive. The reused local cache contains a generated `.bytecode-fingerprint`; it does not establish native equivalence. The immutable archive comparison passes.

All 36 UI tests pass. The [native check](native-sealed-30b383f1.json) passes all 716 tests in 38 files against this exact archive. The live SSH fixture uses only the owned qualification guest at `.214`. Installed candidate acceptance passes. The candidate preserves the selected model and completes a real FlashNext reply. Native HTTP save and recall, actual dashboard restart, complete package reapplication, authenticated rollback, and token revocation pass. The integration run executes 1,030 cases. It passes 1,028 and reports one failure and one error. Both are unchanged process-boundary cases that cannot inspect the workstation sshd-session at `/proc/814420/exe`. All eight unchanged cases pass under the disposable guest service account. This is passing case coverage across two environments, not one clean complete run. HTTP client acceptance and the three product review rounds remain in the [source verification record](../2026-10-16-http-memory/README.md).

The owned disposable guest is CT110, cloned from the retained stock Hermes snapshot. Production receives the complete package after qualification. No personal data import, reset, provider return, or software removal forms part of this promotion. HTTP access starts disabled on existing servers. Tailscale configuration and external agent enrollment remain separate owner actions.


The [installed update receipt](installed-update-recovery.json) verifies use of the original token and fact after both package transitions. It compares complete HTTP configuration and credential-file bytes across rollback. It does not claim a byte comparison across the preceding update.

Operator checks require correction during qualification. Temporary preboot service masks correctly prevent first-install preparation. The operator removes only those owned masks after confirming the synthetic guest has no Discord token. The first model invocation inherits a permissive file-creation mask and creates a group-writable cache. The backup policy refuses that directory. The operator uses mask `0077` and corrects the owned synthetic directory to `0700`. Finally, the protected `/health` route returns a sign-in redirect. Actual authenticated MCP recall verifies restart readiness. A subsequent post-update connection refusal occurs during dashboard startup. The replay waits boundedly for the listener and preserves the original credentials. These corrections change test operators, not product policy.


The [initial certificate](RELEASE-CERTIFICATE.json) binds the exact archive and qualified receipts. Its SHA-256 is `b4bb7f49d5b79fdca0b69dfe55a9d0752664eeef61d66f11a7a8e31beeb7f32c`. Publication preserves this checkpoint. Later public deployment and recovery acceptance require separate evidence assets. The [primary integration result](archive-integration-30b383f1.json), [raw output](archive-integration-30b383f1.stderr), and [service-account replay](installed-process-boundary.stderr) retain the actual outcomes. No test assertion or product policy changes to avoid the workstation refusal.


The [publication receipt](release-publication.json) verifies all three new assets and preservation of all 61 earlier assets. The initial certificate remains unchanged. The GitHub tag lookup returns 404 while the release remains a draft without a Git tag. The owner release ID API verifies the draft and all assets before publication. The published tag and latest stable release then verify as `v0.7.0`.

The [development preparation](development-public-preparation.json) verifies the public archive, production certificate, and unchanged active 0.6.0 package. The authenticated owner selects Update plugin and Review release in the existing dashboard session. The [review](development-owner-release-review.json) binds the expected package and requires no native remount. Protected backup completion precedes application.
