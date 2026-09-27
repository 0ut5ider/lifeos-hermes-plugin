# Isolated LifeOS test environment

As of 2026-09-27, the development fixture is an unprivileged Linux account with a fresh Hermes installation and a fresh clone of the public LifeOS repository. No LifeOS data was copied from an existing installation. The principal is the fictional `Test Operator`.

## Installed baseline

- Hermes v0.21.5+3604.g758ad51, with a local model, a LAN dashboard, and no messaging channel in this test account.
- LifeOS at commit `5e2f2e8`, deployed into `~/.hermes` with `DeployCore.ts --config-root ~/.hermes --apply`.
- A fresh personal tree from `ScaffoldUser.ts --config-root ~/.hermes --apply`, linked by `LinkUser.ts --config-root ~/.hermes --apply`.
- LifeOS's shipped Hermes sidecar mount, including its identity renderer and guard plugin.
- LifeOS's 74 native Claude Code hook registrations installed in the test account, plus the separate `lifeos-hook-bridge` Hermes plugin.
- Bun 1.4.2 and ripgrep 15.2.0.

The installer detects Hermes, but its deployment tools default to `~/.claude`. Pass `--config-root ~/.hermes` explicitly. One runtime generator still writes to `~/.claude`, and many shipped files refer to that path. The fixture uses `~/.claude` as a link to `~/.hermes` until the path behavior has been mapped and addressed. This link is a test workaround, not a portable plugin installation method.

Hermes's stock `research` skill collides with LifeOS's `Research` skill in the LifeOS installer's case-insensitive collision check. The fixture backs up the stock skill outside Hermes's skills directory and installs the LifeOS skill. A distributable installer needs a deliberate policy for this collision.

Identity substitution also replaces placeholder literals in LifeOS's installed `InstallEngine.ts`. The fixture restores that file from the public release after substitution. This is an upstream installer issue to account for in automated setup.

## Verified behavior

- `Mount.ts --check` reports that the identity file and config are current.
- A live Hermes CLI turn answers `Test Operator` when asked for the principal name.
- The mounted guard passes its 61 shipped policy tests.
- The dashboard remains active and rejects an unauthenticated API request with HTTP 401.
- LifeOS Doctor reports identity rendering and filesystem search live.

LifeOS Doctor now reports that every registered hook interpreter resolves. The bridge executes mapped events through the Hermes plugin API and two generic core extensions in the test fork. The [hook parity record](hook-parity.md) identifies unverified effects and missing events. Full hook parity has not been verified. Optional external services such as voice, Cloudflare, browser verification, and a GitHub login are not configured in the fixture.
