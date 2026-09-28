# ISA structural Stop gate through bridge transcript

Date: 2026-09-27. Target: isolated `lifeos-hermes@192.168.8.212` account.

A disposable `ISA.md` declared `phase: complete` with `progress: done` and an unresolved item under `## Not yet specified`. The bridge recorded a synthetic successful Hermes `write_file` tool call in its private transcript. LifeOS's `parseTurnEvents` found one `edit` event for the ISA path. The native `ISAGate` report found two hard violations: `progress-format` and `fog-at-complete`.

The installed `StopGates.hook.ts` wrapper read the bridge's Stop payload and returned a block containing both violation codes. The bridge converted it to `action: continue`. A new native regression test passed on `.212`. The local suite passed 87 tests with seven optional native skips.

The first probe invoked `ISAGate.hook.ts` as an executable and saw no output. That file exports `run()` but has no command entry point. The installed StopGates wrapper is the registered executable and produced the expected block. The probe wrote no persistent LifeOS state.
