Date: 2026-10-15
Role: Independent focused code reviewer, delegated by the primary Cerebo agent
Question: Does the reviewed removal select the exact retained bridge before issuing its installation lease, while preserving current authorization and recovery boundaries?
Model: gpt-6.1-sol, high reasoning effort

## Disposition

CLEAR for the bounded source-selection correction at `f8e0d25b8af2701dc784f36ccba6afb15b78a24c`. I found no remaining actionable defect in the reviewed change. Fifteen local tests pass with clean output, including five independent admission and race controls. This result does not certify a normal first apply through the installed browser, complete removal qualification, reboot, or a real model turn.

The review started against `d417234faa8f15b25f9abfa81efa5dc5a6e6b9ae` with the correction in the working tree. `commit-source-check.json` confirms all seven captured files match the subsequent correction commit byte for byte. No product files, Git state, remote systems, memory records, or journal records were changed by this review.

## Original failure and correction

The primary agent measured that first apply chose the active bridge and issued its typed installation lease before publishing the removal marker. RemovalPublication then loaded the retained bridge. The two copies have distinct Python module namespaces, so the retained bridge correctly refused the active bridge's lease. The reported installed operation stopped before draining or active software removal. The original strict lease refusal remains an explicit passing control.

`memory_workflow._source(profile, workflow=identifier)` now selects `removal_state.prepared()` only for the exact private removal job with ready review metadata and its exact plan signature. `execute()` calls it before acquiring the lease. The existing marker path remains unchanged. Preparation metadata continues to choose the active bridge; unsupported review states refuse. The change does not alter `installation_lock` or its lease type checks.

The primary red receipt contains one passing original lease refusal and five expected missing-keyword errors. It establishes the missing selection API, not five independent authorization failures. I preserved that output, the primary green output, the baseline source, and the supplied safe installed failure receipts. The installed receipts are supplied evidence, not observations made by this reviewer.

## Verification

Command:

```text
python3 docs/verification/2026-10-15-memory-portability/run_tests.py review-removal-execution-source-current test_removal_execution_source docs.agents.2026-10-15-removal-execution-source-review.source_probes test_memory_removal_workflow
```

Result: 15 tests pass in 44.105 seconds. Runner duration is 44.323 seconds. Both process and runner exit codes are zero. `unhandled_diagnostics` is false. I read the full stderr output. Actual synthetic user-service fixtures use the existing service-manager serialization lock and clean their owned units.

The six product controls reproduce strict namespace lease refusal, then prove the new selection reaches real RemovalPublication `verification_required` with actual unique services and unchanged memory. They also check changed retained bytes, wrong signature, incomplete preparation, live owner revocation, and an unknown workflow.

The four existing manager controls check explicit Discord disablement, owner and cross-job restrictions, separate apply after recovered preparation, and retained authority after active configuration removal.

The five independent controls in `source_probes.py` use real copied bridge namespaces, private metadata, real owner grants, and synthetic services:

| Control | Measured result |
|---|---|
| Issue a transition grant through the active namespace, then run actual manager ready cancellation through the retained source | Cancellation succeeds. The grant is revoked. No marker is published. Memory, active program, and configuration remain. |
| Revoke the owner in live policy after grant issuance | Actual manager execution refuses with PermissionError before marker or software changes. |
| Change the review signature immediately after source selection returns, before lock acquisition | The exact grant binding refuses the changed signature. Software and policy remain. |
| Change a copied retained source file at the same boundary | Request bridge identity refuses the changed source before action. |
| Publish another valid private job's removal marker at the same boundary | The selected workflow binding refuses. The other marker is preserved; active software and policy remain. |

The boundary probes use a Python trace callback at the return of the actual `_source` function. They mutate real fixture metadata or copied files and then continue actual `execute()`. They do not replace source selection, locks, authorization, publication, or manager dispatch with mocks. The complete first apply path is not mocked or represented as covered by ready cancellation.

## Admission and recovery assessment

Selecting retained code before the lock is necessary to issue the lease from the same module namespace used by the publisher. The under-lock checks still reload the private request, check the selected live removal marker, compare bridge identity to the reviewed request, and validate the current transition grant against action, workflow, request digest, and review signature. The grant's writer must equal the request owner. Removal dispatch then checks the retained plan owner, selected verified return identifier/signature, and explicit Discord disablement.

Retained configuration still reads the live owner policy while it exists and honors owner revocation. The retained policy supplies recovery authority only after the active policy is absent. The retained configuration cannot save or update native configuration. Publication preflight and the existing retained-source and program identities remain in place.

The measured changes after source selection all refuse under these checks. Existing live-marker selection and cross-job restrictions remain intact. The exact retained source is reused for its strict lease rather than weakening lease admission.

## Prior review boundaries retained

The full package component report in `../2026-10-15-final-removal-review/final-removal-review.md` and contained-dependency-link report in `../2026-10-15-dependency-links-review/dependency-links-review.md` remain the preceding evidence. This review does not reopen their closed findings or broaden their claims. Exact runtime execution identity, covered link targets, native data barriers, generated-output retention, later built-in edits, and the narrow coordinator exemption remain required.

The contained dependency correction at `033af302` remains separately clear in its component scope. Historical archived `4db` and `bb947` runs do not qualify this source-selection correction. The primary reports that an old `033` retained helper rejects a wrong password and admits a correct password for recovery. That existing operation's recovery does not establish normal first apply with this new correction. I did not access a guest or read raw personal data to extend that evidence.

## Captured source identities

SHA-256:

| File | SHA-256 |
|---|---|
| `optional/lifeos_release_manager/memory_workflow.py` | `1054843511c3b06664c485ee98efeef81b7dbeb2324f6c354ffd31db95314cd0` |
| `optional/lifeos_release_manager/removal_state.py` | `d34488f7b09e02a31a2e3d1d05c6b19420192e5881adc6d9253186cdcad6d7e6` |
| `optional/lifeos_release_manager/removal_workflow.py` | `04e5cb16f7dd27644042edef58c815ebc34be12440005ec36c94246eeb2643e2` |
| `optional/lifeos_release_manager/removal_publication.py` | `2c014c8fbf8412f4723960b86eec06ce692043190093db85d5ae2f4f9af3cb2f` |
| `lifeos_hook_bridge/installation_lock.py` | `56fa2ea36fec3186b9954eafe34f622ecc1c230280b96a0db7bca773eb43d417` |
| `lifeos_hook_bridge/memory_administration.py` | `da5e625f94c4a3e8619a7c2531eea4c6f6c53d3aec060b34c0d840f447fc75c1` |
| `tests/test_removal_execution_source.py` | `2ca5fdcd42c86547eecfd02d853f2ddceb300fa9023ffacd9ff984e9766b64c6` |

The baseline memory_workflow source SHA-256 is `d4c28fe12d2be370246d08a048b934cdd404e88fb961e2886ac4104319170838`. Exact captured source bytes are in `source/`; the baseline is `memory_workflow_baseline.py`. `source_probes.sha256` identifies the independent probe module.

## Saved evidence and remaining acceptance

`review-removal-execution-source-current.{json,stdout,stderr,done}` contains the complete independent run. The five named safe JSON receipts describe the independent controls. The primary red/green receipts and safe installed failure receipts have `primary-` prefixes. `commit-source-check.json` records the matching correction commit.

The next acceptance must use a package that includes this correction and perform normal first apply through the installed owner workflow. It must then verify retained recovery, stock constructor behavior, later built-in data preservation, and the authorized full removal qualification. This review makes no claim that those installed steps have completed.
