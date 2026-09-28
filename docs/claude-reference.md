# Claude Code hook reference

As of 2026-09-27, a separate unprivileged account on the test host runs Claude Code 2.1.272 with a fresh LifeOS installation. It uses LifeOS commit `5e2f2e8`, the same public source revision as the Hermes fixture. Its principal is the fictional `Test Operator`. No personal LifeOS data was copied into this account.

The account uses the local `flashnext-w4a16-fp8ple` model through an Anthropic-compatible LAN gateway. Its main launcher supplies `ANTHROPIC_BASE_URL`, `ANTHROPIC_AUTH_TOKEN`, and model names from a private file with mode `0600`. It starts Claude Code at medium reasoning effort, which the gateway accepts. The gateway rejected the default high effort with HTTP 400. The CLI prints an unrecognized-model warning but completed the tested prompts using the requested local model.

The reference account can reach the LAN and loopback addresses only. A user-specific firewall rule persists through a systemd service. This blocks an accidental request to Anthropic or another external service, including one from a LifeOS child process. The gateway token and firewall configuration remain on the test host and are not in this repository.

## Native installation and checks

The installation ran LifeOS's `InstallSettings.ts`, `DeployCore.ts`, `ScaffoldUser.ts`, `LinkUser.ts`, `InstallHooks.ts`, and `ActivateImports.ts` against `~/.claude`. Hook installation registered 74 hooks across 11 Claude Code events and installed 97 hook files. `Doctor.ts --hooks` found no unresolved hook interpreters. These are installation checks, not a claim that every hook behavior has passed an end-to-end test.

An interactive Claude Code turn with the synthetic account completed a `UserPromptSubmit` sequence and a `Stop` sequence. It read the principal identity file and replied with `Test Operator`. The prompt processing observability record for that session has `source: inference` and `latency_ms: 9559`. A direct LifeOS inference test returned `READY` using the local model. Earlier one-shot tests also returned the synthetic name. The model gateway and nested call path were exercised; full hook parity remains unverified.

## Local model adapter

LifeOS's `LIFEOS/TOOLS/Inference.ts` removes `ANTHROPIC_API_KEY`, `ANTHROPIC_AUTH_TOKEN`, and `ANTHROPIC_BASE_URL` from the environment of its child Claude process. Its stated purpose is to use a Claude subscription. In this setup, that would bypass the local gateway. Before adding the adapter, prompt processing logged `source: inference-failed`; the outbound firewall prevented external contact.

The reference account places a `claude` adapter earlier in `PATH` for LifeOS child processes. The main launcher invokes the real Claude Code binary by absolute path. The adapter reloads the private gateway settings and maps child `--model` arguments to `flashnext-w4a16-fp8ple`. Both the reference and plugin launchers now map Haiku to `low`, Sonnet to `medium`, and Opus/Fable to `xhigh` reasoning effort. This changes neither the LifeOS source nor its registered hooks. Neither adapter supplies four distinct models because the fixture has one local model.

The reference child adapter now maps Haiku to low, Sonnet to medium, and Opus and Fable to xhigh. The [alignment record](../notes/2026-09-28-reference-tier-alignment.md) gives the tests and rollback path. The main `lifeos-reference` launcher remains at medium for reference turns.

For the reference account, run `~/.local/bin/lifeos-reference` over SSH to start an interactive session. The private environment file, adapter, and outbound rule must remain in place for local-only operation. To remove the firewall rule on the test host, stop and disable `lifeos-claude-ref-egress.service`; its stop action removes its nftables table. No production LifeOS installation was changed.
