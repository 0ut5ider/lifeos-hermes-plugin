2026-10-15
Role: Independent code reviewer
Question: Does the fresh ownership connector fix preserve owner authority, current data, and interrupted publication safety?
Model: gpt-6.1-sol, high reasoning effort

# Fresh connector review

Reviewed commit: `cde82c079fb977c02899aafb45801a3a18c50633`.

The review identifies one P2 finding with two affected mutation sites. The current change must preserve later connector edits across its final writer check.

## R1. P2: The final writer check invalidates the connector identity check

`lifeos_hook_bridge/memory_ownership.py:214-219` checks that the connector is absent, then calls `verify_writers()`, then publishes the generated connector. `:287-291` checks the generated digest and mode, then calls `verify_writers()`, then deletes the connector.

The actual writer check runs external service queries. A connector can change while that check runs. Neither path checks the current target again after that check. The application path overwrites a later owner connector. The recovery path deletes a later owner connector and returns successfully.

Both effects reproduce on actual temporary files and real user services. The tests use `sys.settrace` at the return of the real `ProfileServices.verify_stopped()` call. The trace creates or edits the connector at that boundary. It does not replace the service query or product function.

1. Prepare a synthetic activation whose native backup records the missing connector.
2. For application, create a different connector at the return of the ownership transaction's final writer check.
3. Application replaces that file with the generated connector. The preservation assertion fails.
4. For recovery, first apply the fresh activation.
5. Change the generated connector at the return of the final writer check before connector deletion.
6. Recovery deletes the changed connector. The preservation assertion fails.

Exact reproductions:

- `connector_controls.ConnectorControls.test_application_preserves_connector_created_during_final_writer_check`
- `connector_controls.ConnectorControls.test_return_preserves_connector_edit_during_final_writer_check`

The full import path is `docs.agents.2026-10-15-fresh-connector-review.connector_controls`. Use the frozen runner with a unique `review-connector-*` label. `commands.json` records the exact commands. The red receipts and complete raw unittest output are retained.

Expected correction: Run the actual writer check before the final current-target check for both connector mutation paths. Refuse a later file or changed identity before the write or deletion. Check the same ordering for adjacent configuration writes. No change to service admission or native data restoration is needed.

## Passed controls

Five independent controls pass:

1. Another dashboard account cannot create the connector or stop the services.
2. Recovery refuses later connector content before it changes configuration.
3. Recovery refuses a later connector permission change.
4. Recovery retains a later native fact and the existing forget decision.
5. A real child process exits immediately after connector deletion. A fresh recovery completes, keeps the connector absent, and restarts the original services.

The first independent run loads these five controls before the two fault reproductions are added. `independent_five.py` preserves that five-control source. The final `connector_controls.py` includes all seven controls.

Existing ownership, setup, and activation regressions: 32 PASS in 156.174 seconds. The five independent controls pass in 42.998 seconds. Each of the two finding reproductions fails at the intended preservation assertion, with no product exception or unrelated test failure.

The primary agent subsequently reproduces both findings and starts a correction. This report reviews only the pinned cde82c07 change. It does not approve the subsequent working-tree correction.

## Scope and limits

The review inspects the connector fix, its setup integration, and adjacent ownership authority, backup, and writer boundaries. `source-pin.json` records byte hashes and verifies that the inspected files match the reviewed commit. The source snapshots and patch are retained.

The tests use synthetic native memory records, actual SQLite and filesystem operations, actual isolated systemd user units, and real process exits. The existing service fixture serializes manager changes and cleans up its owned units. This is component and service integration evidence. It does not prove installed browser acceptance, a model turn, repeated activation after provider return, complete removal, reboot, or release qualification.

The review does not change product code, remote hosts, personal records, memory stores, credentials, commits, branches, or releases. The primary agent must reproduce the finding and review the fix before qualification.
