# LifeOS plugin for Hermes

This project will connect a LifeOS installation to Hermes through a separately installable plugin. The goal is to preserve LifeOS's hook behavior while keeping the integration outside the LifeOS repository.

**Status:** Project scaffold only. No hook integration or installer is implemented yet. Do not use this repository as a replacement for a working LifeOS installation.

## Compatibility target

- Load LifeOS context and skills from a configurable installation path.
- Map each LifeOS hook behavior to a Hermes lifecycle point and verify its effect, including blocks, approvals, context injection, and stop gates.
- Keep the LifeOS installation unchanged where possible. Record any Hermes core extension needed for behavior the plugin API cannot express.
- Test locally on one host first. A remote LifeOS installation is a separate deployment mode.

See the [LifeOS installation guide](https://github.com/danielmiessler/LifeOS/blob/main/LifeOS/INSTALL.md) and the [Hermes event hook reference](https://hermes-agent.nousresearch.com/docs/user-guide/features/hooks) for the current upstream contracts.

## License

MIT. See [LICENSE](LICENSE).
