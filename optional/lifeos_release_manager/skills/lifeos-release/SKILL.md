---
name: lifeos-release
description: Install, update, check, or recover the complete LifeOS integration from Hermes.
---

# Complete LifeOS releases

Use this skill when the user asks to install or update LifeOS, check its integration version, or recover an interrupted release operation.

The complete release includes the supported Hermes source, LifeOS source, bridge, release manager, dependency closure, and Hermes dashboard. Select the integration release version. The release certificate selects the supported Hermes version and native patches.

1. Run `hermes lifeos-release status` to find current operations.
2. Run `hermes lifeos-release prepare` to prepare the latest stable integration release. Use `--version X.Y.Z` only when the user selects an exact version. For a first installation, add `--name` and `--assistant` with the names the user supplies.
3. Read the returned operation identifier, version, commit, package hash, and state. Preparation does not select the new programs.
4. Ask the installation owner to open the LifeOS releases tab in the authenticated Hermes dashboard. The owner reviews the exact operation and selects Install this release.
5. For a command-line installation without managed native memory, the owner can run `hermes lifeos-release start IDENTIFIER`. A native mount with managed memory requires the authenticated dashboard owner grant.
6. Run `hermes lifeos-release status IDENTIFIER` after Hermes restarts. Report the actual state. If it is applied, run `hermes lifeos-version` and report the verified version and commit.

To check whether LifeOS can patch this Hermes installation in place, run `hermes lifeos-release compatibility`. Report the state, the detected version and commit, and each reason. The command changes nothing. Its exit status is 0 only for a compatible installation.

An operation in preparation_failed has not selected new programs. An operation in recovery_required needs owner review. Use the dashboard recovery control or `hermes lifeos-release recover IDENTIFIER` when the owner authorizes recovery. An existing installation can select its retained prior programs with the dashboard control or `hermes lifeos-release rollback IDENTIFIER`. The first installation has no prior integration release.

Rollback requires the current release identity and retained native mount. A later native remount or release can expire the earlier rollback. Use the current status response. Do not offer a historical applied operation as restorable without its restore_available flag. An expired operation refuses before service interruption.

Report queued, preparing, applying, recovering, and restoring as unfinished states. Report rejected and rolled_back as actual outcomes. Do not report installation success from configuration validation or a queued worker.

Keep the current model and tier mapping. Use the prepared operation and its fixed profile. Do not edit an operation request, plan, certificate, owner grant, or private journal. Do not read credentials or memory records to diagnose an installation. Do not replace user data, import data, start a background job, or send a messaging substitute as part of release preparation.

The manager uses qualified assets from `0ut5ider/lifeos-hermes-plugin`. An unpublished candidate or an older release without the frozen dependency closure is unavailable through this workflow. Report that result. Do not substitute an unqualified archive or disable the native plugin scanner.
