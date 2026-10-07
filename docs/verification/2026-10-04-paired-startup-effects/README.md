# Paired startup context and terminal effects

Date: 2026-10-04. Eight cases run through actual Claude Code 2.1.272 and Hermes lifecycle events in synthetic profiles. All 16 command-line runs and selected hooks exit with status zero. Seven cases have matching required effects. One case demonstrates the existing remote terminal isolation difference. The overall runner exits with status one and retains that difference as a failed equality assertion.

| Case | Observation |
| --- | --- |
| `context-desktop` | Both hooks return the synthetic relationship note, 95 percent wisdom principle, and advisory finding. Both exclude the 50 percent principle, preserve source files, and record the current advisory keys. |
| `context-disabled` | Both hooks return a neutral ready message. Disabled dynamic sources do not appear, and no advisory marker is written. |
| `context-remote` | Both hooks withhold unmanaged owner context under the Discord channel environment. Neither writes an advisory marker. Both record session timing. |
| `context-subagent` | Both hooks withhold context and session timing under the forked-subagent environment marker. |
| `context-advisory-steady` | Both hooks suppress an unchanged finding and increment its quiet-session counter. |
| `context-advisory-cleared` | Both hooks clear prior finding keys after an explicit empty finding set. Neither repeats the retired warning. |
| `kitty-remote` | The standalone native hook persists inherited Kitty environment and removes the previous title. The patched Hermes hook preserves the previous title and writes no environment state. |
| `kitty-subagent` | Both hooks preserve the existing title and write no terminal environment for a forked subagent. |

The [retained driver](paired-lifecycle-driver.py) blocks UserPromptSubmit before inference. Each client emits SessionStart, UserPromptSubmit, and SessionEnd with a consistent session identity. No model generation request occurs. Hermes makes two model metadata probes per case. These cases verify hook output and file effects. They do not establish delivery into an actual model request or response.

[paired-results.json](paired-results.json) retains all eight cases and the remote Kitty mismatch. Each client directory retains exact hook input and output, event payloads, source file hashes, command output, and before and after file contents. [runtime-manifest.json](runtime-manifest.json) verifies the unchanged client and plugin sources against the preceding fixture. Each selected hook records its own source identity. The managed source has MemoryAccess, while the standalone native source does not.

The mismatch is the behavior that the existing [remote desktop gate patch](../../../patches/lifeos-remote-desktop-gate.patch) changes. The [earlier terminal record](../../../notes/2026-09-28-remote-terminal-state.md) explains its purpose. The fixture sets a channel environment in real CLI sessions. It does not run a Discord gateway or a real subagent. There is no Kitty server; visible terminal rendering remains outside this comparison. The ledger adds only the seven equal cases. It does not classify the remote case as equal or close complete terminal parity.

Bubblewrap mounts private temporary storage because the native timing helper writes a global `/tmp` file. The root filesystem remains read-only except the synthetic home and device mount. [isolation-probes.json](isolation-probes.json) retains the four startup probes. The read-only device cases exit with status 134; device access restores successful startup. The [failed source capture](failures/missing-native-dependency.log), [failed isolated run](failures/native-readonly-device-run.log), and [Bun crash](failures/native-readonly-device-crash.log) remain available. The [contemporaneous note](../../../notes/2026-10-04-startup-fixture-isolation.md) records the investigation.

The cumulative effect ledger has 24 equal selected cases for 12 registrations. Nine unavailable native dispatch controls and broader handler branches remain open. Active `.212` services and their installed code remain unchanged. Memory ownership stays disabled. The complete release gate remains open.
