# Remote channel voice gate

Date: 2026-09-28. Test host: isolated `.212` account.

LifeOS's `notification-channel.ts` treats a hook process with `TERM` as a desktop session unless `LIFEOS_NOTIFICATION_CHANNEL` says otherwise. Its VoiceCompletion, PromptProcessing, LoadContext, and voice guard paths use this check. Hermes supplies a `platform` value to prompt and Stop plugin hooks, but the bridge discarded it. A gateway process with `TERM` could therefore let a Discord turn reach a desktop voice path.

The regression gave the bridge `TERM=xterm`, a Discord platform, and native hooks at SessionStart, UserPromptSubmit, PreToolUse, and Stop. Before the fix, the UserPromptSubmit child saw no explicit channel. The bridge now remembers the Hermes platform per session and sets `LIFEOS_NOTIFICATION_CHANNEL` for nonlocal surfaces. The channel reaches tool hooks, which do not receive Hermes's platform field directly. SessionEnd clears the mapping. CLI, TUI, and desktop surfaces keep LifeOS's existing terminal detection.

After the fix, the regression passed. A direct call to LifeOS's native channel helper returned `discord` for the Discord turn and `desktop` for the CLI turn with the same `TERM`. All 91 plugin tests passed on `.212` with the native hook paths configured. The installed bridge file matched the tested source, and the restarted dashboard returned HTTP 200. This probe did not play audio or use a real Discord session.
