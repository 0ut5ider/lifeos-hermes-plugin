# Paired permission input replacements

Date: 2026-09-28. The first Write evidence pair used different interventions. Claude Code changed only the target path; Hermes changed both the target path and content. They could support a general statement about replacement behavior, but they were not a controlled pair. A new Claude Code 2.1.272 run changed both fields. Its PostToolUse input named `rewritten.txt` with `MODIFIED`, the original file was absent, and the replacement file contained `MODIFIED`.

The comparator at `scripts/compare_parity.py` now checks three synthetic PermissionRequest cases from saved raw artifacts: a Bash command replacement, a Write path and content replacement, and an MCP argument replacement. It compares final tool input and observed effects, normalizing only the temporary directory prefix of the Write target. All three cases matched. The native runs used the private local model. The Hermes results came from the `.212` installed plugin manager and real terminal, file, or MCP dispatch; its bridge source hash matched the repository source.

This is outcome evidence for those three interventions. It does not prove that Claude Code and Hermes request permission at the same point, show the same approval prompt, handle later policy changes the same way, or execute all 74 installed LifeOS registrations. Those remain explicit gates in the parity plan.
