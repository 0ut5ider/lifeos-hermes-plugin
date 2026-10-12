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

The development reboot exposes native gateway unit regeneration. `gateway run` replaces the stable launcher with a copied package launcher that has no committed dependency environment. The gateway enters a restart loop. The operator retains the failing unit and selects the stable launcher with `gateway run --external-supervisor`. It removes obsolete package-manager stop commands and uses systemd control-group termination. The daily unit already uses external supervision. The final installed gate must verify the development reboot with this fixed unit.

External supervision alone does not stop native unit refresh. The native gateway searches the account HOME for systemd definitions even in that mode. The daily unit already selects the isolated LifeOS HOME, so it does not find and rewrite the account unit. Development now selects that same isolated HOME. The failed first installed check and both prior unit definitions remain retained.

Development reboot preserves the fixed gateway unit and starts the gateway with zero restarts. Dashboard and Pulse units were disabled at boot. The release operator enables these existing units and starts them. The daily guest already enables all three units.

The final sealed package passes 529 combined cases and 12 separately selected source-review cases. These runs cover 541 distinct integration cases. The inherited combined list omits the source-review module, so the complete module runs separately against the same immutable package. Both runs verify unchanged plugin hashes. Native Hermes controls pass 96 cases against byte-identical prepared sources. The native post-forget capture proof passes after explicit review of four synthetic sources, with no duplicate event.

The second development reboot starts all three enabled services without manual intervention. The gateway unit remains byte-identical and every restart count is zero. The post-reboot installed check confirms all 202 plugin files, native programs, and a real private model conversation. The retained program rollback also passes.

Daily 0.3.0 selection preserves 155 files and model settings. Installed source, authenticated dashboard, private audience, and actual model acceptance pass. Launch review accepts five of six selected sources and refuses the retained work-event ledger. An owner diagnostic through the governed snapshot processor finds 12 processed rows and six pending rows. One processed row is unsafe; no pending row is unsafe. The native adapter ignores string timestamps at or before its cursor. The bridge currently validates and copies every raw row. The correction must validate and copy only native-selected pending work rows, preserve complete raw ledger fingerprints, and retain refusal for private pending rows. Published 0.3.0 artifacts remain immutable. The correction uses version 0.3.1.
