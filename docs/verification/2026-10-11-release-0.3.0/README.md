# Integration release 0.3.0

Date: 2026-10-11. Adrian authorizes the versioned release workflow, active development installation, combined acceptance, whole-guest recovery, and daily promotion.

The release preserves selected model routes and existing personal stores. It uses the existing Hermes and LifeOS source pins and all 36 native patches. Daily promotion requires the exact final package, combined acceptance, and whole-guest archive recovery.

The active development gateway initially declares version 0.1.0. The daily gateway initially declares version 0.2.0. Atlas retention passes in isolated development profiles and PR9 merges at 194c334b.

Version work adds matching stable, dev, and rc declarations and the read-only `hermes lifeos-version` command. The command reports unrecorded builds honestly, detects changed or extra plugin files, and distinguishes staged candidates. It makes no model request. The dependency probe selects the existing ruamel.yaml library. Initial command fixtures need a class-placement correction and the actual native TaskGovernance path. Those intermediate results remain retained.

The final version and command gate passes all 15 tests with no skipped tests. A sealed development package is next. No daily release promotion has occurred at this checkpoint.

The first sealed package runs 529 integration tests. It passes 520 cases and fails nine fixture setups. The package omits the optional sharing source required by the memory-preferences tests. The build includes that reviewed source for testing. The guest installer selects only the core plugin and does not enable optional sharing. The failed output remains in `combined-final.*`.
