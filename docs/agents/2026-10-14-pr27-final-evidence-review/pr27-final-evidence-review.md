# PR27 final evidence review

Date: 2026-10-15

Role: Independent completed-evidence and verifier reviewer

Question: Do the corrected owner-search verifier and completed development receipts support the tested qualification checkpoint, and are current owner remount effects represented accurately?

Model: gpt-6.1-sol, high reasoning effort

## Verdict and scope

CLEAR for the corrected owner-search verifier, the corrected supplementary admission helper, and the independently tested **33-case certifier snapshot**. No measured issue remains open in those reviewed changes.

The primary is adding current admission, native skill review, and later-remount scope gates to the certifier. Those future **41-case guards are not covered by this verdict**. They require their own green controls and closure review. This report does not approve a future certifier revision or authorize publication by assertion.

The product program remains `04efe633296eb2b1a1d95561ca6d3e9516cd47dc`, archive SHA-256 `a6dd0e11b8fb1b5ae30345be20c955db02728839f7bc907f60a70944ad392813`. Earlier product, stock verifier, qualification closure, and retry reviews remain separate checkpoints.

The isolated 33-case certifier snapshot SHA-256 is `5eb2fc23045c71b45936c165dba7239309d52361633b214cc90decacab460f5f`. Its complete input identity map is retained. The input files remained unchanged during the independent run.

## Corrected owner-search verification

The actual development save committed. The actual new conversation performed two successful exact synthetic searches. The earlier verifier incorrectly required all searches before the last one to be argument refusals. That condition could reject a correct repeated read.

The corrected verifier validates every successful response. Each must contain exactly one match with the expected reference, exact synthetic content, project category, exact project, terminal writer, active status, and original save session. It accepts only the exact known argument refusal shape for rejected responses. It requires the final response to succeed and requires at least one successful search.

The surrounding verifier still checks the two distinct installed Hermes sessions, private model, process results, one actual remember call, committed write receipt, correct writer and source session, search tool names, tool result counts, absence of tool errors, and exact active product identity. The change permits repeated verified reads, not arbitrary intermediate responses.

Independent results:

- The actual 13 owner-search controls PASS.
- Eight additional sequence controls PASS. These cover interspersed known refusals, three exact successes, two matches before the final success, two matches in the last response, missing matches before or at the end, refusal-only sequences, and a nonexact refusal shape.

The tests execute the actual search validation statements using bounded synthetic unit data. They do not create a guest completion receipt. I did not read the raw controlled conversation streams.

The safe actual diagnostic independently records two exact queries, two successful single-match responses, exact synthetic references and content, and no argument refusal. The safe final owner-turn receipt records two distinct sessions, one committed synthetic reference, two successful searches, zero argument refusals, and the exact active product identity. These receipts agree with the corrected validation behavior.

## Actual development application checkpoint

`development-verification.json` reports PASS for operation `4eac8d1b398e47138d80f8b67b6df596`. It records applied state, 222 sealed program targets, exact verified 0.5.0 identity, unchanged model and tier selection, unchanged credential and owner memory configuration bytes, and all three active services with preserved HOME and profile values.

That receipt is the actual post-apply, pre-owner-remount checkpoint. It must remain historical evidence of that state. It is not a claim that the old release-bound journal remains available after a later legitimate owner remount.

The original failed operation and rollback remain separately recorded. The exact original native Mount stderr remains unavailable. The successful retry and corrected source admission do not prove that the missing launcher was the first attempt's only cause.

## Current native skill admission and remount scope

The safe native skill receipt records 56 exact-package program skill digests reviewed through the authenticated owner path. It records 56 admitted skills, zero omitted program skills, no personal sources reviewed, no native skill byte changes, and a committed owner remount. I examined only this safe receipt, not private source maps, principal values, or personal context.

The receipt's `gateway_restart_pending: true` describes the receipt's checkpoint. The later supplementary receipt records the post-remount active identity and configuration/service checks after the primary's restart operation. It must not rewrite the earlier checkpoint to suggest that the restart had already happened there.

I raised the expected release-journal interaction before certification. An owner remount replaces the native mount journal with an owner action that is not bound to the earlier release operation. The old release restore path correctly refuses that later journal. The primary measured this behavior and retained `development-post-remount-restore-availability.json`:

- The exact release operation remains applied.
- Restore and recover availability are false.
- The original read-only release verifier refuses with `The native mount journal belongs to another release operation`.
- The earlier sealed program receipt is explicitly a historical checkpoint.

This refusal protects later owner changes. It is not a reason to overwrite or rebind the native journal. The new current admission receipt is supplementary identity, configuration, and service evidence; it does not replace the historical 222-target release proof or claim current rollback availability.

The supplementary helper checks current CLI release identity, model and tier selection hash, both configuration file digests, and all three service process HOME and profile values. Its `gateway_restarted_after_remount` flag records the surrounding operator action. The helper itself measures active current service state and configuration, rather than a before/after process identity.

## Supplementary helper finding and closure

I found one P2 guard gap in the newly added `verify_development_admission.py`: an empty `configuration_file_sha256` map skipped both preserved file reads while the report still claimed both files were preserved. I reproduced the actual empty loop without reading a credential or memory configuration file and reported it immediately.

The primary reproduced the characterization, wrote failing desired controls, and added baseline status/server, exact configuration key, and digest-shape checks. The allowed configuration keys are exactly `.env` and `lifeos-memory.json`.

Independent closure results:

- All eight actual admission helper controls PASS, including empty map, missing key, extra key, failed baseline, wrong server, changed digest, and invalid digest shape.
- Seven independent metadata guard cases PASS against the real safe baseline and negative mutations.

The actual post-admission receipt uses the complete real baseline and remains PASS after the corrected helper runs. The finding is closed. No credential value or private memory record was read by this reviewer.

## Full 33-case certifier reproduction

I copied only the certifier's explicit safe inputs and the actual source review report into an isolated local review tree. I used the real completed development preservation and owner-turn receipts. No missing guest receipt was manufactured.

I ran the actual `check_certificate_controls.py` from that tree. Result: **33 cases PASS**. The unchanged inputs qualify in the temporary positive control. Each of the 32 altered-evidence cases refuses. The test creates temporary local certificates inside its test directories, as explicitly authorized, and removes them with those directories. It does not write the real release certificate, change a release asset, or publish anything.

This run covers the identified 33-case snapshot. It predates the new current-admission, 56-skill, and later-remount scope gates. The primary is running the expanded red/green controls. I make no claim that the new 41-case certifier has passed or that this review covers its future source.

## Execution limits and outstanding work

Independent controls completed in this review: 13 owner-search controls, eight added response sequences, eight admission helper controls, seven independent metadata cases, and the 33-case certifier suite. These are separate groups with some overlapping failure coverage.

Actual development application and private-model memory acceptance now have safe PASS evidence. Current admission and owner remount effects have separate safe evidence. Final qualification still requires closure of the expanded certifier guards and their final actual-input control run.

Publication, public default URL replay, and daily promotion are not complete within this reviewed evidence. No 07:00 wall-clock observation is claimed.

I made no remote or memory call, read no credentials, private maps, personal records, or raw narration, edited no product or operator, and made no Git mutation. I wrote only review artifacts and explicitly authorized temporary local test certificates.

## Artifacts

- `certificate-input-identities.json`: exact 33-case certifier and safe input hashes.
- `certificate-inputs.tar.gz`: exact safe input snapshot and complete control result, compressed for retention.
- `certificate-controls.stdout` and `certificate-controls.stderr`: full 33-case test output.
- `owner-search-controls.tar.gz`: exact local search control and verifier sources and result.
- `owner-search-controls.stdout` and `.stderr`: actual 13-control output.
- `probe_search_sequences.py` and `search-sequence-results.json`: eight independent response sequence cases.
- `post-admission-empty-map.json`: original measured empty-loop finding.
- `post-admission-controls-before.json`: retained pre-fix metadata guard probe.
- `admission-controls.tar.gz`: corrected helper and actual eight controls with full result.
- `probe_post_admission_baseline.py` and `post-admission-controls-after.json`: independent corrected metadata guard controls.
- `reviewed-source-identities.json` and `reviewed-*.py`: exact corrected verifier and helper source snapshots.
- The copied `development-*.json` files: safe actual application, diagnostic, owner-turn, source admission, current service, and later-remount availability receipts inspected by this review.
