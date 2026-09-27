# 2026-09-27: A mapped Edit hook saw no path

The first bridge mapped Hermes `patch` to Claude Code `Edit`. That covered replace-mode edits with a top-level `path`. Hermes also accepts V4A multi-file patches, where target paths live in `*** Update File:` and `*** Add File:` headers. The bridge forwarded the raw patch but no `file_path`, so LifeOS `SystemFileGuard` returned early and could not examine the changed file.

A failing test put a synthetic sensitive line in the second file of a two-file patch. The native-shaped guard saw no path and the bridge allowed the call. The bridge now splits V4A added text by file and runs `PreToolUse:Edit` for each target before execution. The test blocks the second file. The installed public LifeOS fixture has no private deny-list, so the real `SystemFileGuard` cannot demonstrate a private-token block on this machine.

Hook subprocesses previously ran from the LifeOS home, while Hermes tool paths usually resolve from the agent workspace. A separate failing test showed both the process directory and `cwd` payload were the fixture root. They now use the agent process directory. Hermes can still configure a different task workspace, so relative-path parity requires another check against that configuration.
