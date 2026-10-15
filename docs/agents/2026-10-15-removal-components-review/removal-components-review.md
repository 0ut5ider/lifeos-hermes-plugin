# Removal components review

Date: 2026-10-15

Role: Independent read-only reviewer.

Question: Do the removal safety components preserve current data, program identity, owner authority, and service recovery?

Model: gpt-6.1-sol, high reasoning effort.

Captured checkout: `9b204dad936ef4b5f04da801cfa059acf4cbd838`. The initial brief named 4f1acb32. The checkout has advanced before this review starts, so source-hashes.json records the exact reviewed files.

Disposition: Three measured P2 findings require correction. The supplied combined component and ProgramTransaction suite passes 40 tests. Four additional boundary probes fail intentionally for the findings below.

This review covers components. It does not certify a removal coordinator, dashboard removal actions, standalone helper launch, full installed end-to-end removal, or a qualified stock runtime release. Those features remain pending.

## Findings

### 1. P2: Inventory admits unreviewed software below LIFEOS program directories

Location: optional/lifeos_release_manager/removal_inventory.py:51 through line 62.

The inventory checks all expected public program files. It then searches for additional software only below hooks, skills, agents, commands, and test. It does not search the corresponding LIFEOS program directories for additional files.

The probe adds LIFEOS/TOOLS/OwnerCustom.ts to the actual synthetic native tree. Inventory admits the removal plan. The plan retains the owner tool but removes the native dependency tree. An actual ProgramTransaction applies that plan: the custom tool remains, and node_modules disappears. The test restores the selected programs afterward.

This violates the first supported layout's refusal of unqualified software. The same added file under hooks already causes refusal. A custom native tool can remain after its dependencies and supporting programs disappear.

Evidence: extra-native-tool.json, review-removal-native-addition.stderr, and component_probes.py, NativeInventoryReview.test_extra_native_tool_refuses_unqualified_removal.

Required correction: Validate unreviewed files and links across the admitted native program roots, with explicit exclusions for user stores and retained runtime data. Refuse unsupported owner software before selecting shared dependency deletion. Preserve the owner file during refusal.

### 2. P2: A new override can stop an unrelated reviewed service before refusal

Location: optional/lifeos_release_manager/removal_services.py:132 through line 140.

The stop method validates known file identities, reloads the manager, and then checks each service immediately before stopping that service. It does not check every current service binding before the first stop. A newly added drop-in is not one of the known file identities.

The probe prepares removal with real fixture services and an inactive disabled Pulse unit. It adds a Pulse drop-in before calling stop. The stop method stops the gateway, then discovers the unreviewed Pulse override and refuses. Dashboard stays active. The gateway PID changes from a live PID to zero.

The override already exists before the stop call. This is a missed preflight, rather than an unavoidable definition change during a drain.

Evidence: added-pulse-override.json, review-removal-boundaries.stderr, and component_probes.py, ServiceDefinitionReview.test_added_pulse_override_refuses_before_gateway_stop.

Required correction: Reload and validate all current definition bindings before stopping the first service. Keep the per-service checks during the drain to catch changes that occur afterward. The refusal must preserve all service processes when the unreviewed override exists before admission.

### 3. P2: Directory retention creates another unchecked input boundary before candidate publication

Location: optional/lifeos_release_manager/release_programs.py:224 through line 248, and the corresponding resume path at lines 304 through 327.

The new per-entry checks improve file publication and initial directory admission. Directory publication then moves the current target into the retained snapshot. After that move, it checks only that the target remains absent before it installs the staged candidate. It does not recheck the retained directory, candidate source, and staged copy at this second boundary.

Two actual filesystem probes demonstrate the gap:

1. At directory-retained, change before-0/program.py. Apply publishes the candidate and records applied. An immediate check_applied refuses because the retained prior program no longer matches its recorded identity.
2. At directory-retained, change incoming-0/program.py. Apply moves that unreviewed candidate into the active target. It eventually refuses through the final target check, but the changed candidate is already published. The journal remains applying.

The first probe permits a completed apply state with an invalid recovery copy. The second probe catches the mismatch after publication. Neither behavior satisfies the intended check of the target, source, and retained copy immediately before publication.

Evidence: retained-edit-before-candidate.json, staged-edit-before-candidate.json, review-removal-boundaries.stderr, review-removal-staged-candidate.stderr, and component_probes.py, PublicationReview.

Required correction: Recheck all directory publication inputs after retention and before candidate installation. Refuse with the changed retained artifact intact and the changed candidate still outside the active target. Apply the same boundary check to resume and the corresponding restore transition. Keep final verification of both selected and retained identities before reporting completion.

## Passing behavior and repair context

The current supplied tests exercise removal configuration transformations, exact inventory, real user services, retained owner authority, native password authentication, default-profile admission, and program transactions. All 40 tests pass in 12.593 seconds.

The configuration tests use the actual stock gateway parser. Discord remains disabled even when an environment token exists. They also check preserved model settings, credentials, unrelated plugin settings, and nested YAML selections.

The retained-state tests confirm that recovery keeps the original profile boundary, refuses writes through retained authority, and honors a live owner revocation. Authentication tests use BasicAuthProvider.complete_password_login. They refuse the wrong password, wrong username, another owner, and public configuration permissions.

The generation tests cover the single default account layout and refusal of another profile or native home. This review does not independently repeat the primary agent's installed-generation inventory on a remote guest.

The baseline includes the primary agent's new publication checks. Existing tests now cover later target edits between file publications and later empty-directory replacement. Those controls pass. Finding 3 covers the next directory boundary after retention.

## Stock-only tool preparation

The captured release_payload.py uses tool_roots(_lockfile().names()) before prepare_tools for a stock-only runtime. Source inspection finds no additional measured defect in this change.

primary-stock-tools-green.json is a clearly labeled copy of the primary agent's safe receipt. It records clean hermes version, hermes-agent, hermes-acp, and configuration commands. It also records qualified_release false and selected_live false. This reviewer does not claim to rerun that stock construction.

The primary agent separately reports that a fresh stock constructor probe currently encounters unexpected memory configuration flags and is investigating profile selection. That report is not an independently reproduced finding in this component review. Fresh full stock construction and constructor acceptance remain required before removal qualification.

## Method and limits

The reviewer changes no product code, reads no personal data, accesses no remote hosts, and calls no memory or journal tools. All reproduction data is synthetic.

The tests use actual native memory components, actual BasicAuthProvider authentication, actual ProgramTransaction file operations, and actual user-systemd service fixtures. Service mutations use the existing fixture serialization. The later-override probe removes its added override and reloads the manager during cleanup.

Publication probes use the transaction's checkpoint at the real directory-retained boundary. They change actual retained or staged files. They do not replace the filesystem or service manager with a mock.

The baseline test_removal_services writes its normal tracked verification artifact, removal-service-layout.json. This is a test side effect. The reviewer does not reset that artifact or modify product files.

The primary agent receives each measured finding and the exact test names before edits. This report applies to the captured hashes. It does not certify subsequent fixes.

## Source and raw evidence

source-hashes.json records all 15 captured component and test files. source/ preserves their exact bytes. Runner JSON receipts, completion markers, stdout, and stderr remain beside this report. component_probes.py contains every reproduction.

Key SHA-256 values:

| File | SHA-256 |
| --- | --- |
| removal_configuration.py | 052f78046651ca45753ee415fc1034967f459e1000d78dba3eb81d23f06515da |
| removal_inventory.py | 58c981674a923c26f0c92fd83e3242fedac3811005baa4a5b0f9aa569d4c01d2 |
| removal_services.py | 49568d10c8175ff1af95cb10782d5f063f9e2ae9f7af26fc913ea5bf5cc23a9e |
| removal_state.py | 6ce6a29f23548fa507b261e963ba5e057beacfd52ad95a5c24318ce226655730 |
| removal_recovery.py | 3d726f7ad9746ffa94cf19e08f075bae55353669b1f66d47b02a8babdf7c5ce7 |
| removal_generation.py | ab2b9cbcd0fbf943dbebe2cf02b672549b1daa5fd7f73f0c95daa6e27c1b4e6c |
| release_programs.py | 31fbbd039216876413b8b4a1c30409c581f369b9a791dac48982cd3d08c345d6 |
| release_payload.py | 3046452897e9e18fe78bb3a557faf7d7f7f523f16a295eb29b7941a15d1ffa20 |
