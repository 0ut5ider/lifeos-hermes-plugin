# Independent agent reports

Dated directories retain review reports, raw findings, repeated checks, and synthetic fixtures. Their source snapshots preserve the reviewed input. They are not active product source or a substitute for a later release certificate.

Start with a report linked from the relevant [verification record](../verification/README.md). A review result applies to its named head and scope. Read follow-up corrections and primary verification before treating a finding as resolved.

The [October 16 documentation audit](2026-10-16-documentation-audit/documentation-audit.md) identifies the navigation and stale-guidance issues behind the documentation cleanup. The [PR36 review](2026-10-16-pr36-review-r1/pr36-review-r1.md) covers the 0.7.2 setup interface.

The [October 16 codebase cleanup](2026-10-16-codebase-cleanup/codebase-cleanup.md) links the runtime, release, and dashboard audits, both dashboard review rounds, and primary verification. It is local source evidence; deployment qualification is separate.

The [minimal installation architecture review](2026-10-16-minimal-install-review/minimal-install-review.md) compares in-place Hermes patches, local-source reuse, split release components, and upstream extension points. Its [primary verification](2026-10-16-minimal-install-review/primary-verification.md) adds independent tests and exact Hermes and LifeOS source-derivation checks. This is a proposal, not an implemented installation mode.

The October 17 [owner decision and implementation plan](../in-place-installation-plan.md) selects in-place patching as the only installation path. It supersedes the review's private-runtime recommendation. Preserve the original report as the alternatives analysis.

Keep each report's question, date, model, reviewed source, evidence, and limits explicit. Put the full report and raw data on disk. The primary agent must check claims and repeat relevant checks before using a delegated result.

Keep personal memory, credentials, raw private traces, model narration, and private export contents outside this archive. See [contributing](../../CONTRIBUTING.md) and the [private recorder guide](../../development/README.md).
