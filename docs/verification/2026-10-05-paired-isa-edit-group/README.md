# Paired complete Edit hook group

Date: 2026-10-05. One case runs all seven registered Edit hooks (`PostToolUse.9.1` to `9.7`) through a real Edit call in Claude Code 2.1.272 and Hermes. Both clients complete with status zero, and every model request succeeds. This is the first case that covers a complete registered group. The run uses the development container and the current plugin commit.

The fixture is an ISA at `MEMORY/WORK/pair-run/ISA.md` with one open criterion and a `started` time one minute before the run. A git repository with one changed file is on the checkpoint allowlist. The model replaces `- [ ] ISC-1:` with `- [x] ISC-1:`.

| Hook | Required effect | Result |
| --- | --- | --- |
| ISASync | The work registry has the run with phase `execute`. The render state lists the ISA. The hook returns the phase strip, and a later model request contains it. | Both clients pass. |
| ISAStaleWriteGuard | The session view holds the hash of the edited content. | Both clients pass. |
| CheckpointPerISC | One commit with exactly the changed file. The state file records `ISC-1` and the new commit. The repository is clean. | Both clients pass. |
| ConfigEvalFire | No output and no evaluation state, because the ISA is not a sentinel. | Both clients pass. |
| AtlasEventCapture | No hint. | Both clients pass. |
| KnowledgeWriteGuard | No output, because the file is outside the knowledge tree. | Both clients pass. |
| ComplexityRatchet | No output for this small edit. | Both clients pass. |

## Recorded difference

The checkpoint commit messages differ. The stock hook writes the subject `ISC-1 (pair-run): Paired criterion closes`. The plugin's `lifeos-checkpoint-verification.patch` writes a conventional subject, `chore(checkpoint): ISC-1 (pair-run): Paired crite`, and puts the stock text in the body. The patch is deliberate: it keeps subjects under 50 characters and verifies the commit. The check requires the stock text in the message on both sides. [isa-edit-proof.json](isa-edit-proof.json) asserts the exact format for each side.

Claude Code needs the `bypassPermissions` mode for this write, because the ISA is below its configuration directory. See the [knowledge guard record](../2026-10-05-paired-knowledge-guard/README.md).

## Evidence

The proof independently reads the raw captures, the edited ISA, the session view, and the checkpoint repository on each side. Each client folder retains the edited `ISA.md`. [runtime-check.json](runtime-check.json) verifies the 17,583 prepared source files of the [current runtime](../2026-10-05-paired-tool-failure-text/runtime-manifest.json). Three of the seven hook files differ between the two trees in program lines. See [source differences](../../parity/source-differences.md).

The new tests fail before the implementation ([before-output.txt](before-output.txt)). The focused suite passes 108 tests. This is one selected case. Phase changes, resume after completion, the Write and MultiEdit groups, and the other branches remain open. The cumulative ledger contains 82 equal selected cases for 34 registrations. Complete compatibility remains unverified.
