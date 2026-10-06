# Paired ISA Write group and Read

Date: 2026-10-05. Two cases run in Claude Code 2.1.272 and Hermes with real file tool calls. All four clients complete with status zero, and every model request succeeds. The fixture matches the [Edit group unit](../2026-10-05-paired-isa-edit-group/README.md): an ISA in `MEMORY/WORK/pair-run` and a dirty git repository on the checkpoint allowlist.

| Case | Registrations | Required effect | Result |
| --- | --- | --- | --- |
| Create an ISA with a closed criterion | `PostToolUse.8.1` to `8.7` | The same effects as the Edit group: registry entry, session view, render state, phase strip, one checkpoint commit with the changed file, no hint, no evaluation state, no knowledge or complexity output. | Both clients pass. |
| Read an existing ISA | `PostToolUse.7.1` | The session view holds the hash of the file. No registry entry, no render state, no checkpoint, and the repository stays dirty. | Both clients pass. |

The Write prompt gives the complete ISA text, including a `started` time one minute before the run. Both clients write it exactly.

The checkpoint subject differs by the plugin's checkpoint patch, as in the Edit group unit. Claude Code needs the `bypassPermissions` mode for writes below its configuration directory.

[isa-write-read-proof.json](isa-write-read-proof.json) independently reads the raw captures, the ISA, the session view, and the checkpoint repository on each side. [runtime-check.json](runtime-check.json) verifies the 17,583 prepared source files of the [current runtime](../2026-10-05-paired-tool-failure-text/runtime-manifest.json). See [source differences](../../parity/source-differences.md).

The new tests fail before the implementation ([before-output.txt](before-output.txt)). The focused suite passes 111 tests. The cumulative ledger contains 84 equal selected cases for 39 registrations. Complete compatibility remains unverified.
