# LifeOS plugin for Hermes

This project connects an installed LifeOS hook set to Hermes through a separate plugin. The goal is to preserve LifeOS's hook behavior while keeping the integration outside the LifeOS repository.

**Status:** Experimental test fixture. The bridge runs native LifeOS hooks at matching Hermes events. Full hook parity is not yet achieved. Do not use this repository as a replacement for a working LifeOS installation.

## Compatibility target

- Load LifeOS context and skills from a configurable installation path.
- Map each LifeOS hook behavior to a Hermes lifecycle point and verify its effect, including blocks, approvals, context injection, and stop gates.
- Keep the LifeOS installation unchanged where possible. Record any Hermes core extension needed for behavior the plugin API cannot express.
- Test locally on one host first. A remote LifeOS installation is a separate deployment mode.

See the [LifeOS installation guide](https://github.com/danielmiessler/LifeOS/blob/main/LifeOS/INSTALL.md) and the [Hermes event hook reference](https://hermes-agent.nousresearch.com/docs/user-guide/features/hooks) for the current upstream contracts.

The [hook parity record](docs/hook-parity.md) lists mapped events, tested effects, and missing behavior. The isolated Hermes installation and its current limits are recorded in [docs/test-environment.md](docs/test-environment.md). A separate [Claude Code reference installation](docs/claude-reference.md) uses synthetic LifeOS data and the same local model to measure native hook behavior.

The bridge needs the [Hermes core extension](patches/hermes-hook-controls.patch) for Stop and approval behavior. The [LifeOS task patch](patches/lifeos-task-governance.patch) lets the native TaskCreated hook use a Hermes session count. Apply the [LifeOS watchdog patch](patches/lifeos-agent-watchdog.patch) after the task patch to route background agent silence alerts through Hermes. These patches are tested on the isolated `.212` checkout. The hook parity record describes their exact base revisions and remaining limits.

## License

MIT. See [LICENSE](LICENSE).
