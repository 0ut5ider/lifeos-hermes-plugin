# LifeOS Bash guards and Hermes execute_code

On 2026-09-28, I compared the installed LifeOS PreToolUse registrations with Hermes `execute_code`. LifeOS registers `PreToolGuard.hook.ts` for Bash, Write, Edit, and MultiEdit. Hermes `terminal` maps to Bash, but an outer `execute_code` script previously reached only generic hooks. Hermes approves the whole script in some contexts; that approval does not execute LifeOS's command-specific guards. An `execute_code` script can also call Python subprocess and file APIs without making an inner Hermes tool call.

The bridge now presents the source of an outer `execute_code` call as `tool_input.command` to named Bash PreToolUse hook groups. Generic groups still receive the original `execute_code` name and `code` input. A Bash hook can block the script. The bridge ignores `updatedInput.command` from a Bash hook because a shell rewrite cannot safely edit Python code.

The regression failed before this change because a Bash matcher did not run. It passed afterward, including a check that the generic group ran once and a Bash rewrite did not change Python arguments. The `.212` plugin suite passed 114 tests. A direct bridge probe ran the installed native `PreToolGuard.hook.ts` with a synthetic Python script containing `os.system("bun gmail.ts send")`. Its `CommunicationSkillGuard` blocked the script before execution. No email send or Python script ran.

This covers literal source patterns the native Bash guards recognize. Dynamically built commands, computed file paths, and other Python effects can evade a text scan. The bridge does not claim that those operations have the same enforcement as a Claude Code Bash command.
