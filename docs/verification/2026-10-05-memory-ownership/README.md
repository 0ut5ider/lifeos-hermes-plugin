# Reviewed ownership configuration transaction

Date: 2026-10-05. These controls use private synthetic Hermes profiles, native LifeOS storage, actual Hermes processes, and a local scripted model endpoint.

`OwnershipTransaction` prepares the two configuration changes from a reviewed profile backup. The preview checks the authenticated dashboard owner, disabled ownership and sharing, exact current configuration bytes and modes, and the installed native memory connector. The native connector must match the verified backup. The plan signature covers both selected configuration digests, the connector digest, the owner, the profile, the native root, and the backup signature.

Setup writes `memory.provider: lifeos-hook-bridge`, `memory.memory_enabled: false`, and `memory.user_profile_enabled: false`. It preserves unrelated mapping values, quotes, and comments with the existing Hermes YAML dependency. Shared YAML anchors and merged memory settings require review. Setup refuses malformed or duplicate settings. This unit adds no dependency or upstream patch.

The private journal records intent before publication. Setup disables both built-in stores before enabling native ownership. It rechecks the verified backup, the connector, and already published configuration before the second write. Interruption leaves recoverable configuration state. Recovery revokes native ownership first, then restores the exact prior Hermes configuration and modes. It checks all targets before recovery and checks each target before its write. Later configuration edits cause a refusal. Native data, current references, later facts, and forget decisions remain in their current live store.

The initial feature controls fail because the ownership transaction does not exist. Later controls reproduce a restore that overwrites an intervening edit, an uncaught journal state type, setup that enables ownership after its first configuration changes, connector loss, and three shared or merged YAML forms. The raw failures and their command specifications remain in this directory. The first test launch fails during collection because it imports PyYAML in a runtime that uses `ruamel.yaml`. The corrected feature baseline uses the existing dependency. No dependency is installed to resolve that fixture error.

The fresh-process sequence verifies built-in configuration, selected LifeOS configuration, and exact configuration return. The selected process exposes the native memory tools and `skill_manage`. It excludes the built-in memory tool and both preserved memory markers. Actual built-in writes refuse. A complete `AIAgent.run_conversation` sends one Chat Completions request to the local endpoint. That request excludes both built-in markers. The final response is the actual scripted endpoint response. A fresh returned process reads the preserved built-in files again.

The final regression passes **44 tests and 36 subtests in 68.53 seconds**, with no skips, failures, or errors. It includes the ownership controls, profile backup and recovery controls, existing actual Hermes ownership controls, and installation lock checks. Fourteen individual ownership outcomes are retained.

The final command, source hashes, prepared source manifest, process output, and exit status are retained in `final-command.json`, `final-output.txt`, and `final.done`. Individual synthetic outcomes are in `native-outcomes/`. The preceding 43-test regression and its 33 subtests remain under `pre-alias-final-*`. The last YAML refusal change receives a new final regression because it changes the accepted configuration formats.

## Scope and remaining requirements

This is an internal configuration transaction. It has no dashboard or Hermes activation command. A caller must stop and drain the selected profile writers before using it. The caller must rebuild agents and verify the service and owner turn after it. Every receipt reports `service_verified: false` and `restart_required: true`. Configuration commit does not establish complete ownership setup or production readiness.

This unit does not coordinate gateway, dashboard, native PULSE, background jobs, program restoration, or dependency restoration. It does not prepare a fresh native prompt or the HTTP relay. Configuration rollback preserves current LifeOS data; it does not import facts back into the built-in stores or remove the integration. The source inventory, restricted prompts, scheduler authority, private FlashNext acceptance, aggregate recovery, and complete release gate remain open.

No deployed profile, production ownership setting, personal data, live service, pull request, or remote branch changes. Shared-memory MCP access remains blocked by its previously observed integrity error. No file access bypass is used.
