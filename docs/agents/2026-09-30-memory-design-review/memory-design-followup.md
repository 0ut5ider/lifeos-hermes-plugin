Date: 2026-09-30
Agent role: Independent reviewer, bounded documentation follow-up
Question: Do the primary documentation amendments close the design gaps without changing ownership or claiming unverified behavior?
Model: GPT-6.1-Sol, high reasoning effort (inherited from parent)

# Memory design amendment follow-up

Adrian, the amendments close the three specification gaps identified by the independent review. I found no remaining contradiction that should block synthetic implementation work after the existing hook parity gate passes. The documents continue to distinguish required future behavior from demonstrated runtime behavior. They preserve native LifeOS ownership, native hook recall and review ownership, Hermes history/compression/skill behavior, optional sharing, and the untouched existing systems.

## Scope and evidence

I reviewed only `git diff -- README.md notes/2026-09-30-memory-design.md docs/parity-resolution-plan.md` in the LifeOS_plugin checkout. The exact reviewed diff is preserved in `raw/amendments.diff`. This follow-up adds no source or remote inspection, runtime experiments, code changes, server changes, configuration changes, or memory access. The first review remains unchanged by this follow-up.

## Resolution of the original omissions

| Original gap | Amendment result |
| --- | --- |
| Cross-layer current facts versus retained history | Active, superseded, forgotten, and pending states cover hot memory, archive, searchable learning, and derived context. Ordinary recall excludes superseded and forgotten claims. Explicit history access follows permissions and retention policy. Applied corrections and forget decisions govern native reviewer input, and old material cannot silently recreate a claim. Reactivation requires a new authenticated request with any conflict shown. |
| Privacy before native context exposure | A trusted host policy includes principal, author, participants, visibility, categories, model route, and actual destination. Every messaging app supplies metadata to the same policy. Unknown identity, visibility, or recipients receive restricted access. Enforcement precedes hook output, tool output, rendered context, child inheritance, compression, and reviewer input reaching a model. Destination authorization remains a separate delivery check. |
| Stable references, authenticated provenance, and retries | References cover native note/file, entry/section, revision, and status. Destructive operations refuse ambiguity and stale edits. Writer authentication differs from source provenance. Retry keys resolve previous outcomes. Receipts distinguish committed, unchanged, pending, rejected, conflict, unknown, and partial acceptance. |

The amended native behavior paragraph directly addresses the difficult boundary: authorized contexts retain native hook ownership, cadence, and behavior; restricted-context filtering is an explicit privacy requirement. If native interfaces cannot express that requirement, the design requires a documented extension and comparison tests. It does not pretend that provider or MCP permissions already govern native direct reads, and it does not add a replacement automatic recall path.

The write requirements now cover native reviewers as well as adapters. They establish the invariant that committed changes survive other writers and identify acceptable locking/revision patterns. They do not require choosing or implementing a concrete metadata representation before disposable-fixture feasibility work. The same paragraph retains interrupted publication, archive creation, related-link, guarded deletion, and lock acceptance cases.

Recovery, packaging, profile roots, skills, schema checks, and update/restore remain acceptance gates. Restricted SSH policy, separate proposal creation/approval grants, and active-session revocation remain sharing gates. These requirements make no tested runtime claim.

## Messaging-app equivalence

The design now uses app identity only to obtain trusted account and conversation metadata. Policy applies to authenticated contexts, not app names. Approved cross-app account-ID bindings, current author checks, participant changes, unknown metadata restrictions, and destination-bound context prevent a private conversation in one app from becoming implicit authorization in another.

Adrian's requirement is identical behavior across any connected messaging apps given equivalent authenticated contexts. The existing sentences that memory rules remain the same across apps and equivalent contexts receive equivalent access implement that direction. A small wording refinement would make the claim exact: replace “Equivalent authenticated contexts receive equivalent memory access” with “Equivalent authenticated contexts receive the same memory behavior and access, regardless of messaging app.” This is clarification, not a change to the ownership or permission design.

The planned two-adapter synthetic test is useful evidence that the policy is independent of one adapter. It cannot prove that every supported adapter supplies accurate metadata. The amendment correctly says so. Before advertising full memory support for an adapter, verify its principal/author bindings, visibility, participant and thread metadata, destination changes, scheduled-send context, and permission-change invalidation under the same conformance cases. An adapter without required metadata must retain the documented restricted behavior and expose its capability limit. This is an acceptance refinement, not a demand to build app-specific memory policies or to verify nonexistent future adapters.

## Remaining work and conclusion

No additional storage algorithm or second authoritative store is needed to complete the design. Native representation, metadata persistence, transaction/conflict behavior, correction/forget feasibility, profile integration, and hook context policy remain implementation questions to resolve through synthetic tests. They must pass before enabling ownership or sharing as already specified.

The amended specification is sufficient to proceed after hook parity. The optional wording refinement above would mirror Adrian's equivalence requirement more precisely; per-adapter conformance belongs in acceptance evidence. No implementation, ownership switch, migration, or sharing activation is authorized by this review, and no tests or runtime guarantees are claimed.

## Final current-diff check

The primary applied both wording and acceptance refinements after the first follow-up review. I checked the current design text and refreshed `raw/amendments.diff` from the three documentation files.

The design now states: “Equivalent authenticated contexts receive equivalent memory behavior and access.” This resolves the behavior-versus-access wording refinement.

The design also states: “These tests establish representative evidence. Verify trusted metadata and common-policy behavior for every supported adapter before claiming support. An adapter that lacks required metadata stays restricted and reports that limitation.” This resolves the adapter conformance refinement while preserving one policy across apps.

Both refinements are now resolved. I found no remaining necessary specification amendment in this bounded review. Synthetic implementation can proceed after the existing hook parity gate; ownership and sharing still require the recorded acceptance evidence. This final check used local documentation only and makes no runtime-test claim.
