# Owner review of retained system sources

Date: 2026-10-02. Role: Cerebo, primary implementation and verification.

## Reproduced limitation

A correction or forget excludes older unclassified sources. The actual native prompt renderer therefore refuses an unchanged constitution. The earlier mount contract also refuses an excluded assistant identity instead of removing its launcher denial. Rewriting safe files changes timestamps but does not establish reviewed provenance.

The eight initial cases fail because the preferences service has no source-review operation. [before.txt](before.txt) records the failures. The first corrected prompt and source regression passes 49 cases. [after.txt](after.txt) records that result. The expanded source-review selection passes 14 cases. [review-after.txt](review-after.txt) records that result.

## Implemented contract

The authenticated installation owner can preview installed system Markdown, top-level skill metadata, and the four fixed identity, goals, and project sources. The preview shows source contents only when native validation and known retirement checks accept them. Archive and history sources cannot receive this approval.

Approval binds the exact installation root, principal, relative path, contents, and current effective retirement state. The preview also binds current configuration. Missing owner authority, changed configuration, changed contents, or a changed retirement state prevents approval of an old preview. A matching retry returns unchanged.

The metadata stores a digest, path, principal, approver, review time, and retirement digest. It stores no second fact body. Review changes no native source bytes or timestamps and does not activate memory ownership.

A matching review permits the reader to omit only the conservative age exclusion. Native private-content validation and detected retired-claim exclusion still apply on every read. Restricted contexts still cannot read these sources. Conversation or model contexts cannot invoke approval. Copying metadata into another installation does not transfer approval.

The owner endpoints are `POST /memory/sources/preview` with `paths` and `POST /memory/sources` with `paths` and `signature`. Both use the existing dashboard authentication and private response headers. Unknown request fields cannot grant authority. There is no native model-tool approval endpoint.

## Verification details

The tests use real Bun rendering and mounting with synthetic files. They compare reviewed managed output with native standalone output. They check unchanged source bytes and timestamps, private-content refusal, retired-claim refusal, exact-source invalidation, configuration changes, owner revocation during validation, restricted contexts, copied metadata, and denied model approval.

Authenticated FastAPI requests cover preview, publication, unknown fields, account-binding removal, and anonymous refusal. The first HTTP fixture installs authentication outside the private response middleware and misses the anonymous cache header. [http-fixture-order-failure.txt](http-fixture-order-failure.txt) preserves that fixture failure. The corrected test uses the existing PULSE authentication fixture, which installs middleware in the supported host order. It does not change production middleware or remove the assertion.

Metadata schema 4 adds the approval table. A schema 3 upgrade preserves existing record and operation metadata. A test verifies preserved references and native readback. An older schema 3 plugin cannot read schema 4. A future code rollback must account for this constraint; it must not discard later facts by restoring an old database snapshot.

## Limits and next work

This is an explicit owner-review mechanism, not automatic proof that a source came from a trusted release. A VersionDrift baseline does not grant approval. A new effective correction or forget requires renewed source review. Fresh changed text without a matching review still follows the existing ordinary admission policy.

No preferences-page review controls or automatic installation review are added in this unit. Administrative install, update, and PULSE remount authority remain open. The remaining derived readers, lifecycle, complete restore, ownership activation, and independent release review remain open. No running server changes.

[run_gate.sh](run_gate.sh) selects source review and neighboring native, permission, prompt, wiki, provider, preparation, and patch contracts. Its result is a bounded regression, not the full release gate. The native fixtures use the preceding pinned distributed source tree. The changes are plugin-owned Python code and add no Hermes or LifeOS patch group.

The combined gate passes 193 cases in 159.282 seconds, without skips, failures, errors, or warnings. [gate.txt](gate.txt) records the output. [gate.done](gate.done) records exit status 0. Source identity and plugin file digests are in [verification.json](verification.json). This is primary verification, not an independent review.
