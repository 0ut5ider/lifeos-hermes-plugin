# 2026-09-27: Task governance across Hermes restarts

The bridge originally tracked TaskCreated counts and todo IDs only in Python memory. A Hermes process restart during an existing session reset the count. The patched native LifeOS TaskCreated hook therefore received zero again, which could allow more than 50 tasks in one session.

The bridge now writes a private per-session JSON state after each successful todo or kanban creation. It loads that state on the next task call, including after a bridge restart, and removes it at SessionEnd. A test creates 50 tasks, starts a new bridge instance, confirms the existing 50 are recognized and task 51 is blocked, finalizes the session, then confirms a new task is allowed. A malformed persisted state fails closed at count 50. The state directory is created with mode 0700, and files use the system temporary-file mode before atomic replacement.

This test covers a clean restart after the successful tool result. A crash between tool completion and the post-tool callback can still lose that one task count. The bridge cannot infer whether an unobserved tool call succeeded without reading Hermes's own task store.

The installed patched LifeOS TaskGovernance hook also passed an isolated `.212` probe. One bridge instance accepted 50 synthetic todos and recorded the successful result. A new bridge instance loaded count 50. Its native capability probe returned supported, and the native hook blocked the next task with its own 50-task message. The probe used a temporary LifeOS root and created no real Hermes tasks.
