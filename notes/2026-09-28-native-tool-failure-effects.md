# Native PostToolUseFailure effects

On 2026-09-28, I exercised the three installed LifeOS PostToolUseFailure registrations through the Hermes bridge on isolated `.212`. Every probe used a temporary LifeOS root or home. The bridge received synthetic tool results; it did not execute the Bash commands in the payloads.

- EventLogger wrote a `tool_failure` row with session `failed-bash`, tool `Bash`, and error `Exit code 1`.
- LoopDetector persisted three failed entries for one session and returned `[LOOP DETECTED]` on the third identical failed call.
- AlgorithmNudge read a temporary capability manifest that marked `codex` broken. It returned the static Doctor fix nudge for a failed `codex --version` payload once and returned no nudge for the immediate repeat.

The three native tests passed. The full plugin suite passed 121 tests on `.212` with Bun and the patched LifeOS checkout configured. These checks verify the installed handlers' bridge effects for representative failure cases. They do not test every possible native trigger.
