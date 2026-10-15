# Removal workflow review

Date: 2026-10-15

Role: Independent read-only safety reviewer.

Question: Do the preparation fixes and removal manager preserve current state, exact program selection, owner authority, private browser state, and recovery boundaries?

Model: gpt-6.1-sol, high reasoning effort.

Reviewed commit: `3b01911fb55374acab04a54cd9e887382e278578` on `feature/memory-portability`.

Disposition: The previous two preparation findings close under their original four controls. Two adjacent P2 findings remain. The current Python suite passes 25 tests, and seven SDK component tests pass. Two additional boundary probes fail for the measured defects below.

This report does not certify installed complete preparation, detached stock-worker acceptance, reboot acceptance, or a model turn. The primary agent is performing installed candidate acceptance independently. Their pending status is not a finding in this review.

## Findings

### 1. P2: The selected stock launcher can change without invalidating the runtime review

Location: `optional/lifeos_release_manager/removal_workflow.py:25`, the `_stock` runtime admission function. The stock plan publication in `removal_preparation.py` does not include launcher identities either.

The runtime admission checks fixed path strings, the Hermes source fingerprint, and the manifest file digest. It does not check the content of `stock-runtime/bin/hermes`, `hermes-agent`, or `hermes-acp`.

The generated account commands point at these stock launchers. A later launcher edit therefore changes the program that the owner will run without changing any value that `_stock` checks. The final fresh-agent probe starts Python and source directly, so that probe does not exercise the changed launcher.

Measured control:

1. Copy the actual constructed stock Hermes source and its actual manifest into a private test runtime.
2. Copy the actual `bin/hermes` launcher into that runtime.
3. Record the exact source and manifest identities that `_stock` uses.
4. Confirm `_stock` accepts the unchanged runtime.
5. Change only `bin/hermes` to a harmless shell command that exits with status 91.
6. Confirm `_stock` still accepts the reviewed runtime.
7. Execute the selected command and observe status 91.

The source and manifest identities remain unchanged. The reproduction is an exact runtime-admission component test. It does not claim to execute the complete preparer or full removal.

Probe: `workflow_probes.StockBindingReview.test_later_stock_launcher_edit_refuses_exact_runtime_admission`.

Safe receipt: `changed-stock-launcher.json`.

Required correction: Bind the selected stock launchers to their exact prepared content and check them before dispatch and publication. The final acceptance must establish that the actual selected commands remain the reviewed commands. The same runtime check should define which interpreter, bootstrap, dependency, and command artifacts are immutable, rather than treating unchanged manifest bytes as proof of the artifact bytes they name.

### 2. P2: A loaded runtime-linked foreign service escapes consumer admission

Location: `optional/lifeos_release_manager/removal_consumers.py:21`, the `unit_files` scan.

The scan reads only the account's `.config/systemd/user` directory. Systemd can load an account service from its runtime unit directory or through a runtime link to another physical file. An inactive service has no current process for the separate process scan to find.

The measured control creates one unique actual user service through `systemctl --user link --runtime`. Its `ExecStart` explicitly names the selected private Bun and native program paths. Systemd reports the unit as loaded, inactive, and `linked-runtime`. The service is outside the three reviewed integration roles.

`unit_files` admits that foreign consumer. Removal can then select the software that this unrelated service requires for deletion. The test never starts the foreign service.

Probe: `workflow_probes.ForeignServiceReview.test_runtime_linked_foreign_consumer_refuses`.

Safe receipt: `runtime-linked-consumer.json`.

The test takes the existing `service_manager_fixture` lock. It removes its runtime link and reloads the user manager during cleanup. It does not change any production unit.

Required correction: Inspect the user manager's effective unit load paths and actual fragment and override bindings, or refuse the unsupported foreign layout before removal. Preserve the foreign definition. Do not rely on the absence of a running process to prove the absence of a service consumer.

## Previous preparation findings and measured response

The previous report at `c97c2f6e` found a pre-transaction lost update and three literal consumer bypasses. Their original source remains in `preparation_probes_original.py`.

`preparation_closure.py` adapts only the lost-update probe's new return contract. It unpacks the fourth `expected_before` mapping and passes that mapping explicitly into `ProgramTransaction.prepare`. A tuple-unpacking failure is not counted as closure.

All four controls pass:

1. Later `config.yaml` and `.env` edits cause refusal, and both later settings remain intact.
2. An actual Bun process with basename `argv[0]` is refused through its `/proc/PID/exe` identity.
3. A foreign service with `%h` paths is refused.
4. A retained hook with `${HOME}` paths is refused.

The implementation also carries admitted native file identities, the native settings input identity, qualified retained plugin identities, and qualified launcher and Bun identities into transaction preparation. This closes the measured source-to-before-image gap. The runtime launcher finding concerns the new stock output selected for later execution, rather than the admitted integration launcher input.

## Manager, owner, and recovery assessment

The reviewed manager requires exact removal selection fields, a fixed provider-return workflow identifier and signature, and explicit Discord-disable acknowledgement. It separates preparation from application. The ready review supplies the recovery command before active software removal.

The current controls establish the following behavior:

- The retained installation owner can read status and obtain an exact recovery grant after the active memory configuration disappears.
- Another dashboard owner cannot use retained removal authority.
- Another workflow cannot use the live removal marker.
- Recovery of a completed preparation without a live marker returns the operation to ready. It does not apply software removal.
- The real HTTP routes reject unauthenticated sessions, another account, forged fields, foreign origins, and client-selected paths.
- Real user-service tests resume interrupted publication and preserve later built-in memory on software rollback.
- A fresh actual stock Hermes constructor selects built-in memory after the tested software publication. The control performs no model turn.

The retained worker source selection validates the exact retained bridge and manager file maps before dispatch. Standalone recovery validates those maps before importing retained manager code and authenticates through the actual native basic password provider. Current live owner revocation continues to take precedence over retained policy.

The removal marker also excludes complete-release preparation and worker actions. Software rollback archives the marker only for its exact workflow and review signature. This review finds no new measured cross-job or owner-authority defect in those paths.

The new final verifier checks the native export signature under the removal data barrier, current built-in file identities, native-provider absence, active-plugin absence, and current service state. It rechecks file identities after the fresh child returns. Its direct Python execution does not close Finding 1.

## Browser state controls

Seven actual manager and bridge SDK component controls pass with the installed stock Node 26.7.0 tool. These include the retained earlier-poll ordering regression, explicit Discord acknowledgement, exact verified-return selection, and separate removal application.

The manager removes operations containing private reviewed prompts after an authorization refusal. Its request generation prevents an earlier successful poll from restoring those operations after a later refusal. The status HTTP response uses `Cache-Control: no-store`.

These are SDK component fixtures and real HTTP session controls. They are not a browser acceptance result.

## Evidence and limits

The captured source set has 24 files. `source-hashes.json` records their exact SHA-256 hashes at the reviewed commit. `source/` retains the corresponding bytes. The original and adapted preparation probes are separate files.

`review-removal-workflow-current` passes 25 Python tests. Its runner wall time is 30.180 seconds. `review-removal-workflow-boundaries` fails two assertions for the measured findings, with runner wall time 6.225 seconds. Both receipts preserve actual commands, stdout, stderr, and completion status. `ui-command.json` and `ui-current.*` preserve the seven passing SDK controls.

The reviewer changes no product files, makes no commits, and pushes nothing. All facts and profiles are synthetic. The review reads no remote hosts, personal records, memory tools, or journal tools. No passwords, raw narration, personal memory, or unrelated service command metadata appear in the exported receipts.

The primary agent separately identified a possible second-activation lifecycle problem. It is not reproduced in this bounded removal review and is not counted as an additional finding here.
