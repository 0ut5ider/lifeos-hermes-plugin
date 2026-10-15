# PR27 preparation operator review

Date: 2026-10-14

Role: Independent orchestration and preservation reviewer

Question: Do the waiting development preparation operator, public stock fixture operators, and daily synthetic preservation correction stay within their authorized targets and fail closed?

Model: gpt-6.1-sol, high reasoning effort

## Verdict

CLEAR for the reviewed preparation and fixture operators. I found no actionable active risk that requires the waiting development supervisor to stop. No new measured correctness or preservation issue remains open in this scope.

The earlier product review and the qualification closure remain CLEAR as separate, narrower checkpoints. The product program remains `04efe633296eb2b1a1d95561ca6d3e9516cd47dc`, archive SHA-256 `a6dd0e11b8fb1b5ae30345be20c955db02728839f7bc907f60a70944ad392813`.

This review does not certify development application, public installation, daily promotion, memory effects from a new guest run, or final release publication.

## Brief and source snapshot

The primary requested review of `advance_development.py` while its supervisor waits for the real protected development checkpoint. The operator is uncommitted at the start of this review. The primary also requested the newly committed public CT113 fixture operators.

The primary later added a narrow daily preservation correction. Previous daily acceptance intentionally forgot both older synthetic facts. Actual admitted searches confirm both remain absent. A new synthetic baseline exists through actual owner memory tooling. This review includes the new baseline preparation operator, the changed pure daily validator and daily branch of `verify_promotion.py`, and its controls.

Reviewed files:

- `advance_development.py`
- `provision_public_replay.py`
- `install_public_stock.py`
- `prepare_daily_memory.py`
- `verify_promotion.py`
- `check_daily_memory_controls.py`

`reviewed-source-identities.json` records their exact SHA-256 values. The hashes remain unchanged when this report is written. I did not modify the operators or product code.

## Development preparation findings

The waiting operator polls only the protected checkpoint on Proxmox `192.168.8.101`. It requires the actual completion marker to contain zero, a PASS checkpoint for guest 101, services resumed, no daily guest change, and an archive under the fixed PBS CT101 prefix before it copies or installs anything.

The mutation target is the fixed SSH destination `root@192.168.8.252`. The native manager installation uses the exact GitHub repository, manager subdirectory, and pinned product commit. It then verifies the retained archive SHA-256 and all 21 manager source files against that archive. It compares the credential and owner memory configuration file digests with the pre-promotion baseline. The bootstrap receipt states that the complete integration has not been applied.

The operator restarts only the selected development dashboard and invokes complete release preparation. It exports the safe preparation receipt and requires PASS. It has no package apply, admission, authorization issuance, or recovery grant call. Those actions remain separate owner-reviewed phases.

I also inspected the installed Hermes native plugin installation implementation used by this workflow. It stages an exact-reference source and uses the native publication path. This inspection does not substitute for actual bootstrap verification. The operator's post-bootstrap exact archive file checks are still required.

Local refusal results: **seven cases PASS**. The actual outer try/except block refuses a failed checkpoint marker, expired wait, failed status, wrong guest, services not resumed, daily change, and foreign backup prefix. Every case records failure in memory and reaches no mutation phase. No accepted checkpoint or completion receipt is supplied to the operator in these probes.

## Public fixture findings

The provisioning operator checks the Proxmox inventory for occupied CT113, checks whether `.244` responds, requires the public SSH key, rejects a missing or redirected file-backed storage directory, and checks the named storage before creating the guest. Its only mutation command creates CT113 with hostname `lifeos-050-public-install`, address `192.168.8.244`, the disposable tags, and onboot disabled. It does not stop, destroy, or resize another guest.

Local refusal results: **five cases PASS**. Occupied guest, responding address, absent public key, absent storage, and redirected storage all refuse before a `pct` creation command.

The stock installation operator requires no existing profile configuration, plugin directory, or account native installation before writing its fixture configuration and launchers. It uses a deliberately unreachable synthetic model URL, creates fixture-only credentials, leaves the plugin enablement list empty, and starts a stock dashboard bound to loopback. It does not install the release manager or LifeOS integration.

The `STOCK_DASHBOARD_STARTED` baseline is a fixture startup report. It is not public plugin installation acceptance. The stock source has an external staged-source prerequisite identified by `stock-source.json`; this review does not independently re-extract and compare that runtime. The eventual public replay must still prove its actual installed source and complete release identity. The existing baseline must not be counted as a completed public replay.

## Daily synthetic preservation correction

The new preparation operator authenticates the actual daily dashboard owner before using the governed memory API. It first requires both intentionally forgotten synthetic markers to return an empty successful search. It then remembers one exact new synthetic fact with fixed request ID `stable-050-daily-04efe633`, searches it, and verifies its exact content and returned reference. It refuses to overwrite an existing baseline receipt. It does not read memory records from disk, reset data, import data, or restore either forgotten fact.

The promotion verifier checks the exact safe baseline marker, server label, actual owner save/search and authentication flags, prior-fact absence, no reset/import, reference shape, and positive integer revision. It requires the admitted search to return exactly that reference. The daily branch then independently confirms both forgotten old markers remain absent.

The new reference replaces an invalid expectation that an intentionally forgotten prior fact should still exist. It does not change the model mapping, memory ownership policy, or release identity checks.

I independently reran the actual seven pure validator controls in a local review copy using the real safe baseline metadata. **Seven cases PASS**: exact preservation, absent result, wrong reference, wrong revision, missing owner, wrong marker, and reset/import claim. These are pure validator checks, not fabricated guest acceptance or proof of a new memory write.

## Verification and limits

Independent local checks total **19 passing cases**: seven development refusal paths, five provisioning refusal paths, and seven daily pure validator controls. All six reviewed operator files parse successfully. The refusal probes execute actual outer control-flow blocks with explicit local negative inputs. They never call SSH, Proxmox, services, or memory endpoints. Their marker writes stay in memory.

I read only safe local baseline and preflight receipts. I did not read credentials, personal records, private maps, or raw narration. I did not create or write a release certificate or a guest completion receipt. I made no Git mutation, remote call, or memory call.

The active development backup, actual manager bootstrap and preparation, development owner conversations, final certificate controls, public installation replay, and daily promotion remain with the primary agent. The review gives no substitute success evidence for those operations.

## Artifacts

- `reviewed-source-identities.json`: exact source identities and syntax results.
- `probe_advance_refusals.py`, `advance-refusal-results.json`, `.stdout`, and `.stderr`: seven development refusal cases.
- `probe_public_refusals.py`, `public-refusal-results.json`, `.stdout`, and `.stderr`: five public provisioning refusals.
- `daily-controls.stdout` and `daily-controls.stderr`: actual seven pure validator controls.
- `pure-daily-controls.tar.gz`: the exact local pure control source and safe baseline input copies, compressed for retention.
