# Integration release 0.3.0

Date: 2026-10-11. Adrian authorizes the versioned release workflow, active development installation, combined acceptance, whole-guest recovery, and daily promotion.

The release preserves selected model routes and existing personal stores. It uses the existing Hermes and LifeOS source pins and all 36 native patches. Daily promotion requires the exact final package, combined acceptance, and whole-guest archive recovery.

The active development gateway initially declares version 0.1.0. The daily gateway initially declares version 0.2.0. Atlas retention passes in isolated development profiles and PR9 merges at 194c334b.

Version work adds matching stable, dev, and rc declarations and the read-only `hermes lifeos-version` command. The command reports unrecorded builds honestly, detects changed or extra plugin files, and distinguishes staged candidates. It makes no model request. The dependency probe selects the existing ruamel.yaml library. Initial command fixtures need a class-placement correction and the actual native TaskGovernance path. Those intermediate results remain retained.

The final version and command gate passes all 15 tests with no skipped tests. A sealed development package is next. No daily release promotion has occurred at this checkpoint.

The first sealed package runs 529 integration tests. It passes 520 cases and fails nine fixture setups. The package omits the optional sharing source required by the memory-preferences tests. The build includes that reviewed source for testing. The guest installer selects only the core plugin and does not enable optional sharing. The failed output remains in `combined-final.*`.

Installed acceptance finds a real post-cleanup capture failure. The synthetic Discord forget operation makes older Conduit metadata unavailable under the retirement cutoff. Configuration review already exists. Cursor review lacks a declared `state.json` path. Two actual authenticated HTTP tests fail with HTTP 409 before the correction. The correction adds only that source path. It keeps decoded retirement checks, private-content refusal, byte preservation, and current-source signatures.

The Proxmox backup completes in 927.9 seconds. Immediate service resume fails because the user service manager is not ready after reboot. A later explicit resume succeeds. The restore continues from the completed archive, without another backup.

The cursor correction passes all 32 source-review and Conduit neighboring tests. The first neighbor run lacks its required native control path and retains that environment failure. The corrected run uses the complete declared fixture environment. A root-directory diagnostic also produces Bun `posix_spawn` EACCES because the unprivileged child cannot enter `/root`. Installed commands must use the selected owner profile as their working directory.
