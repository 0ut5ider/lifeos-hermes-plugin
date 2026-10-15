Date: 2026-10-15
Role: Independent PR28 deployment evidence reviewer
Question: Does PR28 accurately bind the actual public installation, daily promotion, current owner mount, complete recovery, and cleanup evidence before supplementary immutable publication?
Model: GPT-6 Codex reviewer. The harness does not expose a more specific backend identifier.

# Verdict

CLEAR for the current reviewed PR28 deployment evidence and certifier. The findings below are corrected. No unresolved actionable finding remains in this scope.

The reviewed closure HEAD is `f648f7a604496da480feac495f848c180fee1499`. `reviewed-snapshot.json` records the exact source and input hashes. The product remains commit `04efe633296eb2b1a1d95561ca6d3e9516cd47dc`, archive SHA-256 `a6dd0e11b8fb1b5ae30345be20c955db02728839f7bc907f60a70944ad392813`. No product change is part of this closure.

The unpublished candidate `DEPLOYMENT-ACCEPTANCE.json` remains SHA-256 `0d6a52ae5a88f0e3874db09ccd13050fa9b0180c626112c136eb58f93f3d1478`. The current certifier reconstructs its exact canonical bytes from the actual safe receipts. The source receipts and candidate bytes did not change during the fixes. The initial release certificate remains SHA-256 `c8a0ac35fa6f084d417951fd7538bee8f9d330ff101a9f71e3855b5da8a2dd20`.

# Brief and review boundary

Adrian authorizes independent review, measured fixes, and repeated review before publication and merge. The primary requests final review of PR28, initially HEAD `a782af1b`, base `ebf5531c`. The scope includes new final evidence, certificate bindings, public native web installation, daily Update plugin actions, exact package identity, seven current owner outputs, generated baseline scope, runtime recovery, Atlas cases, services, model and configuration preservation, cleanup commands, and historical automatic-observation wording.

I read local source, documentation, and safe receipts. I ran local controls against real safe inputs. I did not operate guests, access the network, call memory or journal tools, read private maps, inspect personal records or credentials, alter product or operator source, create guest completion receipts, commit, push, or publish an asset. Mutations exist only in process memory. Copies of existing receipts and candidate bytes are retained as review inputs.

This closure preserves the earlier scoped CLEAR verdicts for the public replay operators, daily editor operator, complete restore guards, source admission, generated baseline proof and Atlas reuse, and cleanup operator. This review does not repeat the complete archive test suites or claim to independently execute the remote deployment.

# Findings and measured closure

## P2: Incomplete recovery and cleanup command binding

The original certifier accepted a successful operation label even when its command targeted a different source or destination. It also accepted extra cleanup commands that could stop the daily guest, storage removal directed at `PBS-01`, and incomplete preserved-guest maps. This could certify evidence that did not prove the stated isolation and preservation claims.

`additional-certificate-gates-before.json` retains the fail-first cases. The primary added exact ordered recovery label and command pairs, exact ordered cleanup commands, strict integer-zero exit status checks, and the complete expected preserved guest map. Current checks are in `certify_deployment.py:22`, `:49`, and `:158`.

All affected original cases now refuse. Independent additional controls also refuse operation reordering, a wrong label, omission of the disconnection command, boolean exit values, and changed processing guest identity or status. The checks validate the exact completed operation, including source CT102, restored CT110, owned rehearsal guests CT111/112/113, and owned storage `lifeos-050-tests`.

## P2: Incomplete daily identity and checkpoint scope binding

The original certifier accepted wrong package or commit metadata in the admission receipt, wrong server metadata, reversed capture and verification actions, a missing source baseline proof count, and a false historical timestamp claim. Those inputs could produce an acceptance receipt with stronger claims than its checked evidence.

The primary added fixed daily server checks, exact selected identity and operation checks, common capture and restored proof requirements, and exact timestamp scope. Current checks are in `certify_deployment.py:74`, `:108`, and `:141`.

All original cases now refuse. Additional controls refuse personal source review, false credential preservation, masking on the source capture, personal record access, absent required native mounting, a new 07:00 wall-clock claim, and incorrect fresh-install metadata for the daily update.

## P2: Separate parse and digest reads could bind unchecked bytes

The original loader read each file once to parse it and again to calculate its digest. A local in-memory fault returned valid receipt bytes for the first read and different bytes with `personal_data_imported_or_reset: true` for the second. The original certifier returned PASS while binding the unchecked second bytes. `receipt-read-binding-before.json` preserves this reproduction.

`load()` at `certify_deployment.py:16` now reads each of the 18 inputs once. It derives parsed values and SHA-256 digests from that same buffer. The independent closure probe confirms one read for every input and a hash of the actual validated original bytes. The changed second-read bytes are never used. The primary suite also covers this behavior.

## P3: Current deployment guidance contradicted editor activation

The daily-text guide described the enabled 0.5.0 editor, then said to complete that editor in a later release. The primary replaced the stale paragraph. The guide now separates the current enabled governed editor from the historical first-release disabled editor choice. `initial-documentation.diff` preserves the original contradiction.

# Validation

All commands use `python -W error::ResourceWarning` and operate only in this review directory.

| Check | Result | Raw evidence |
| --- | --- | --- |
| Primary current certifier suite | PASS, 2 positive checks and 31 corruption refusals | `primary-certificate-controls-after.stdout`, `.stderr` |
| Original independent corruption cases against original source | All 17 invalid variants accepted, expected fail-first result | `additional-certificate-gates-before.json` |
| Same independent corruption cases against current source | All 17 refuse | `additional-certificate-gates-after.json` |
| Separate receipt read reproduction against original source | PASS accepted unchecked hash bytes, confirms defect | `receipt-read-binding-before.json` |
| Same read injection against current source | Each input read once, unchecked changed bytes not bound | `receipt-read-binding-after.json` |
| Additional command and metadata boundary controls | All 15 refuse | `closure-boundaries.json` |
| Actual candidate and nested public receipt hash bindings | All 24 match | `actual-evidence-hash-consistency.json` |
| Current safe input and source snapshot | Matches live local reviewed files, original receipts unchanged | `reviewed-snapshot.json` |
| Local release asset snapshots | 54 prior records unchanged, 55 assets before deployment evidence publication | `asset-snapshot-comparison.json` |

The refusal counts above describe executed checks. Some controls overlap in purpose. They are not counts of distinct product tests. These are certifier controls against actual inputs, not mocked end-to-end deployment tests.

Reproduction commands from this directory:

1. Run `python -W error::ResourceWarning current/check_deployment_certificate.py`.
2. Run `python -W error::ResourceWarning probe_additional_certificate_gates_after.py`.
3. Run `python -W error::ResourceWarning probe_receipt_read_binding_after.py`.
4. Run `python -W error::ResourceWarning probe_closure_boundaries.py`.

`source/` retains the initial source and safe inputs. `current/` retains the corrected source and the same actual input bytes. The negative probes never write mutated receipt variants or a reconstructed release certificate.

# Actual evidence consistency

The native public web installation uses the default GitHub URL without an explicit ref. Its actual four actions identify operation `568cd8927be849e7a92f0d048999d070`. The original browser observer did not complete after the dashboard restart. The retained read-only completion authenticates again, observes the same applied operation, and records that it does not repeat apply. The separate installation verifier supplies the exact installed identity check. The public acceptance receipt binds both records and the stock source provenance.

The daily native Update plugin record contains preparation, owner review, and queued application for operation `b9e873b251604202a58442b502a3c2b2`. Its review identifies the exact 0.5.0 commit and archive, with `fresh: false`. The separate actual worker verification proves the applied state and all 221 sealed targets. The records distinguish queued application from completed application.

The owner admission receipt records 56 program skills and the constitution, 57 reviewed sources, and zero personal sources. The editor activation receipt records actual owner remounting, 24 declared metadata entries, anonymous HTTP 401, sealed HTTP 403, and the limited configuration change. Subsequent health and preservation receipts retain the exact package, configured private model tiers, credential and memory configuration, service HOME bindings, and all three active services. The captured editor configuration digest matches the post-backup live health receipt.

The protected archive is `PBS-01:backup/ct/102/2026-10-15T03:19:34Z`. The actual ledger identifies the source backup, protection, writer resumption, disconnected CT110 restore, verification, and CT110 deletion. Source and restored runtime maps agree on 64,567 artifacts, 58,080 regular files, 1,650,659,292 bytes, and nine runtime roots. Only safe map hashes are exported.

The current program capture and restored verification agree on 221 selected targets, seven current owner mount outputs, and checkpoint SHA-256 `a5d55d8b6059acc2aee53e846e0715d19a28b280e467d5ad147c7954126a89db`. The proof verifies 1,742 independently derived public program hashes. The baseline timestamp is a strict integer bounded by public publication and original apply intent metadata. Exact original timestamp preservation is not claimed. The older release restore remains unavailable after the legitimate owner remount. The verifier does not rebind that earlier journal.

The three actual Atlas cases agree between the restore summary and Atlas receipt: baseline restores 51 files, interrupted restores 55, and later-edit restores 55 with the later edit refused. The disconnected guest masks application services. The live source resumes its writers. The cleanup receipt removes only CT111, CT112, CT113 and the empty owned test storage. Its preserved guest map retains CT100, CT101, CT102, CT106, and VM801 with their exact recorded identities and states.

The normal morning schedule remains `0 7 * * *`. The acceptance explicitly sets `original_0700_wall_clock_observed: false` and `manual_morning_job_run: false`. The README, TODO, changelog, release record, and deployment guide separate earlier automatic-observation checkpoints from this release. No new scheduled morning execution or substitute Discord delivery is claimed.

# Remaining publication limits

The local safe publication snapshots prove that the 54 assets present before public acceptance retain their recorded metadata. The added public acceptance asset is the sole new asset in the 55-asset pre-deployment snapshot. This is a local snapshot comparison, not a live GitHub recheck.

The primary must still publish the reviewed supplementary asset, compare all 55 existing assets with the pre-publication snapshot, update the final publication record, and merge PR28 under the existing authorization. This report does not claim those actions already occurred. The primary retains responsibility for the live publication recheck.

The riskiest remaining action is immutable publication of the exact reviewed candidate bytes. The review does not authorize changing the product archive, replacing the initial certificate, rebinding the older release journal, or expanding the public fresh-install checkpoint to claim new owner memory activation. No additional product change is required by this review.
