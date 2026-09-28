# ISA close and fold gates with bridge transcripts

Date: 2026-09-27. Target: isolated `lifeos-hermes@192.168.8.212` account.

Both probes used a disposable `LIFEOS_DIR` with an active work registry row bound to the synthetic Hermes session. The bridge produced each transcript from its normal synthetic tool-result path.

For `ISACloseGate`, a disposable nudge state recorded 11 tool calls since the last ISA edit. The bridge recorded a successful Bash result without an ISA edit. The native gate read the transcript and blocked the completion claim `Done.` with `ISA CLOSE GAP`. A small Bun driver imported the gate's `run()` function because the gate file is a library used by the StopGates wrapper.

For `ISAFoldGate`, the bridge recorded a successful synthetic `wrangler secret put TEST_SECRET` Bash call without executing it. The installed StopGates wrapper read the transcript and blocked the turn with `ISA FOLD GAP` because no ISA edit appeared. No secret was created or read.

Three native ISA gate tests passed on `.212`, including the previously verified structural gate. The local suite passed 89 tests with nine optional native skips. These tests verify the three block paths. Other stop gate conditions still need their own evidence checks.
