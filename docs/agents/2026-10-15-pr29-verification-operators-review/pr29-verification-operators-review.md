2026-10-15
Role: Independent PR29 verification-operator reviewer
Question: Can the new fresh-install, backup, cold-restore, and certification operators produce false qualification, mix evidence, target an unowned guest, select the wrong recovery state, or export private content?
Model: gpt-6.1-sol, high reasoning effort

# PR29 verification operators review

**Correction required in the certification driver. One P2 finding, C1, has three measured effects and an additional reproduction with a genuine other-workflow receipt. No additional actionable finding is established in the seven execution operators within static-review limits.**

Product code remains cleared at `c86b5887b899ca779afbb217c33843e1ee12c381`. The immutable 0.6.0 program archive remains SHA-256 `9e2a1939efbaccc94abaa879b265f1af447f9bdfe0b82aecc76f872f15fa9fb7`, 288,167,820 bytes. This review concerns uncommitted verification operators and does not request a program change or archive replacement.

## Exact reviewed scope

`source/` preserves the exact nine initial files. Their repository paths and SHA-256 values are in `source-pin.json`:

- `verify_restored_removal.py`
- `restore_removed_guest.py`
- `verify_fresh_candidate.py`
- `configure_fresh_release_model.py`
- `provision_release_guest.py`
- `bootstrap_release_guest.py`
- `prepare_fresh_release_candidate.py`
- `certify_release.py`
- `test_release_certificate.py`

All nine sources parse. The primary later changes only `certify_release.py` and `test_release_certificate.py` to correct the reported finding. `source-state-at-report.json` records this distinction. This report evaluates the preserved initial versions. It does not clear the later correction before focused closure.

## C1. P2: Certification can accept failed proofs and another workflow's authentication

Locations in the pinned `certify_release.py`: lines 115-119 and 131-145.

The authentication loop checks success flags but does not require the expected workflow or action for each named receipt. The model-session loop requires PASS, a fresh session, an executed model turn, and process success. It does not require decisive stock learning and recall result fields. Therefore qualification can accept explicitly contradictory proof fields or a genuine successful authentication from the wrong operation.

Three independent refusal controls fail against the pinned driver:

1. Set `actual_tool_success`, `later_fact_published`, and `prior_memory_preserved` to false in the stock later-learning receipt. The driver returns QUALIFIED in memory.
2. Set `marker_matched` and `expected_tool_selection` to false and `actual_search.verified` to false in the postboot later-recall receipt. The driver returns QUALIFIED in memory.
3. Change the interrupted recovery authentication receipt to the normal removal workflow and action rollback. The driver returns QUALIFIED in memory.

An additional control substitutes the genuine, otherwise unmodified `installed-normal-rollback-authentication.json` receipt for `installed-060-recovery-authentication.json`. It also fails to obtain refusal. This proves the workflow defect with real existing safe receipt bytes, not only inconsistent synthetic flags. A normal rollback admission does not establish interrupted recovery admission.

The correction must check the decisive successful learning and recall fields for each phase. It must bind authentication to the expected interrupted or normal workflow and expected recover or rollback action. The wrong-password receipt should have the same exact workflow/action binding. The final certificate must not silently substitute a valid success from a different operation.

The existing five negative controls pass because they cover helper validation of package identity, modification state, and removal inventory/state. They do not execute this whole certification path with mixed or failed proof evidence.

## Probe method and raw results

`probe_certification.py` calls the exact pinned `certify()` function with real immutable candidate and normal-removal archives, the real qualified dashboard asset, and copied safe receipt files. It writes changed receipts only to a temporary directory. It supplies a clearly marked synthetic cold-restore bounding fixture so the validator can reach the later validation and return paths while actual cold acceptance remains pending.

The synthetic cold input is not an observation. It is not published or counted as qualification. No certificate file is written. The returned dictionary exists only in the test process. No function is mocked, and no guest, service manager, model, browser, SSH, or Proxmox command runs.

The independent five-control run has two passes and three failures in 16.780 seconds. The positive bound control establishes that the fixture reaches the validator return. The missing-cold control establishes that absent cold evidence refuses. The remaining three assertions require refusal and fail because no ValueError is raised. Raw output is in `certification-probe.stderr`; command arguments are in `certification-probe-command.json`.

The genuine mixed-authentication control fails in 3.282 seconds. Its source, command, and raw output are `probe_real_auth_receipt.py`, `real-auth-command.json`, and `real-auth.stderr`.

The original `test_release_certificate.py` run passes five tests. Its source is pinned and its command, output, and process exit are saved as `existing-tests-*`. The primary independently reproduces the reported failures before editing the certification driver. That separate reproduction is primary evidence, not added to the reviewer counts.

## Seven execution operators

The cold-restore driver checks that guest 111 does not already exist in cluster inventory or local configurations. It refuses adoption through normal `pct restore` behavior. It checks that source guest 110 has the fixture hostname, disposable tag, and disabled boot setting. It creates a protected whole-guest archive, selects the newly added archive, disconnects the restored guest before boot, and checks preserved memory hashes and original guest states. It selects rollback for an already verified restored removal, which matches the retained helper's allowed state. It does not attempt recover on that verified state.

`verify_restored_removal.py` checks the restored hostname and account, authenticates the retained owner, binds the exact workflow and generation, checks the qualified stock commit, and calls sanctioned `RemovalPublication.verify`. That product method holds the installation and program locks, checks current program/service state, uses the native backend writer barrier, compares the native signature, and checks the fresh constructor proof. The operator exports hashes and booleans. It does not replace native consistency proof with raw native file inspection over SSH. The proof explicitly reports no model turn, so constructor success is not represented as inference.

Fresh verification binds the actual applied operation to the exact 0.6.0 commit and archive. It checks current source identity, the sealed program transaction, selected model and tier mapping, original empty native state, and service states. Private and public certificate branches remain distinct. Its model output stays in the private guest directory; only safe proof metadata is printed. The separate post-model verification remains an external required gate and is consumed by certification.

Fresh model configuration reads the provider line through standard input, creates private backups, requires the selected model/provider and absence of active native integration, and publishes the environment and configuration locally. Credentials are not placed in process arguments or exported receipts. Fresh bootstrap creates synthetic dashboard credentials and a dead initial model endpoint. Preparation marks the private candidate as fixture-only and explicitly disclaims public GitHub replay.

Provisioning refuses an existing target slot, creates a separate disposable guest with boot disabled, and verifies original guest states. The bootstrap and guest-side helpers rely on the outer operator selecting that owned disposable target. This source review does not independently establish actual target ownership, network isolation, backup protection, or completed rollback on a host. Those require actual operator receipts and remain primary execution gates.

No additional execution-operator defect is demonstrated within this boundary. All seven remain subject to their actual execution results. The public verification branch has not been executed by this reviewer or counted as completed public acceptance.

## Review closure and remaining gates

The initial certification driver also has no required input binding a final CLEAR operator review to the actual reviewed operator source hashes. The bounded positive fixture reaches QUALIFIED with no operator-review closure file. The primary proposes adding such a checked closure input before certificate generation. This is a required release-gate binding to assess in focused closure; manual publication sequencing alone does not put that review evidence into the certificate.

The next focused review must preserve the initial probes, repeat their three refusal controls and genuine wrong-workflow substitution against the final correction, verify the checked review-closure/source binding, and confirm missing cold evidence still refuses. Actual cold restore remains independent evidence. A synthetic validator fixture must never satisfy that operational gate in release artifacts.

This review does not repeat product code review, change the immutable archive, qualify a release, perform public installation, or approve promotion to development or daily. The reviewer changes only review artifacts and temporary local fixtures. Product source, Git state, guests, credentials, personal records, memory MCP records, and journal records are not changed or accessed by this review.
