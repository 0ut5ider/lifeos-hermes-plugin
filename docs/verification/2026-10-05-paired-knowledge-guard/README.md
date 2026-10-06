# Paired knowledge write guard

Date: 2026-10-05. Two cases exercise the native KnowledgeWriteGuard hook through real Write calls in Claude Code 2.1.272 and Hermes. All four clients complete with status zero, and every model request succeeds. The runs use the development container and the current plugin commit.

This is the first unit that writes inside the LifeOS memory tree. Each client runs with `.claude/LIFEOS/MEMORY/KNOWLEDGE/Ideas` as its working directory.

| Case | Target | Required effect | Result |
| --- | --- | --- | --- |
| Off-schema note | `Ideas/pair-idea.md` without frontmatter | The hook returns the off-schema warning. A later model request contains it. | Both clients pass. |
| Index file | `Ideas/_index.md` | The hook returns no output. No model request contains the warning. | Both clients pass. |

## Permission difference

In the `acceptEdits` mode, Claude Code refuses the write with a safety check: it treats files below its configuration directory as sensitive. A real LifeOS installation keeps its memory tree there, so Claude Code asks the user before a model write to a knowledge note. Hermes writes the file in the project scope without a question. The native control therefore uses the `bypassPermissions` mode. This difference concerns the approval, not the hook effect.

## Evidence

[knowledge-proof.json](knowledge-proof.json) independently reads the raw captures. It checks the hook payload, the working directory, the matcher, the exact warning prefix, the written file, the later model requests, and every response status. The Hermes index case has three model requests and the native case has two. The model chooses the number of calls, so the ledger check excludes the request counts and the hook invocation count of file and repeat cases from its equality rule. `check_pair` still validates each side.

[runtime-check.json](runtime-check.json) verifies the 17,583 prepared source files of the [current runtime](../2026-10-05-paired-tool-failure-text/runtime-manifest.json). The two clients run different LifeOS trees. See [source differences](../../parity/source-differences.md).

The new tests fail before the implementation ([before-output.txt](before-output.txt)). The focused suite passes 105 tests. A valid note, the Edit registrations, and complete groups remain open. The cumulative ledger contains 81 equal selected cases for 29 registrations. Complete compatibility remains unverified.
