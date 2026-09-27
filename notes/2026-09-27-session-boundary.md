# 2026-09-27: A Hermes session hook fired after every turn

The bridge first registered LifeOS `SessionEnd` with Hermes `on_session_end`. Source inspection found that `agent/turn_finalizer.py` emits `on_session_end` after every completed turn. The hook name suggested a conversation boundary, but its observed call site did not. LifeOS has six registered SessionEnd hooks, so this would run them after each message.

Hermes `on_session_finalize` fires when a conversation is closed or reset. The plugin now registers LifeOS `SessionEnd` there and does not register it on the per-turn hook or the new-session reset hook. A registration test failed before the change and passed afterward. The installed plugin validates with the corrected hook name. Native effects at the finalization boundary still need a separate check.
