# 2026-10-05: Hermes does not complete a write to CLAUDE.md in one-shot mode

During the file hint unit, Hermes did not finish a `write_file` call for a file named `CLAUDE.md`. The client printed `Preparing the isolated Hermes runtime` and stayed active until the 120 second limit. The first assumption was a plugin defect in the ConfigChange path. The measurement rejects that assumption.

## Measurement

Three one-shot runs in the development container use the prepared Hermes source and the private model. Each run has a 75 second limit.

| Plugin | Target file | Result |
| --- | --- | --- |
| Disabled | `CLAUDE.md` | No exit within the limit. The file is not written. |
| Disabled | `notes.md` | Exit 0. The file is written. |
| Enabled | `CLAUDE.md` | No exit within the limit. The file is not written. |

The run with the plugin disabled shows the same result, so the plugin hooks are not the cause. No PreToolUse or PostToolUse hook ran in the paired run.

## Cause

`tools/file_tools_write_guards.py` in Hermes has a protected instruction file gate. A write to `AGENTS.md`, `CLAUDE.md`, `SOUL.md`, or `.cursorrules` in any directory always needs human approval, also in bypass mode. The source comment says that the gate fails closed without a human channel. The plugin patches do not change this file.

In one-shot mode the write does not return a refusal within 75 seconds. This note does not establish whether Hermes waits for an approval or for another operation. Claude Code writes the same file in the `acceptEdits` mode.

## Consequences

- This is a Hermes host policy, and the release plan keeps Hermes denials authoritative. It is an intentional difference from Claude Code for these four file names.
- A paired case cannot use those names as a write target. The ConfigEvalFire sentinel branch needs another sentinel, for example a file whose name ends in `.hook.ts`.
- A LifeOS workflow that edits `CLAUDE.md` or `SOUL.md` through the file tools stops for approval under Hermes. On Discord, that approval needs a working approval prompt. This path is not tested yet.
- The absence of a prompt refusal in one-shot mode can be reported to Hermes. It is not a plugin correction.
