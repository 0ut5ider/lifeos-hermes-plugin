# TaskCreated native session key probe

The installed `TaskGovernance.hook.ts` reads `task_description` from stdin, then stores one count in `/tmp/pai-task-governance.json` under `process.ppid`. It does not read `session_id` from the hook payload.

On the isolated `.212` account, a bubblewrap run gave the hook a private `/tmp`. One shell process invoked it twice with valid descriptions and two different `session_id` values. The resulting state was `{"ppid":"2100643","count":2}`. This proves the installed hook merges distinct Hermes sessions when both calls share a parent process. The bridge's current session-scoped reservation prevents that behavior, but it runs equivalent policy code instead of the installed hook.

A portable native invocation needs a LifeOS hook change to key state by `session_id` when one is provided, while preserving the parent-process fallback for Claude Code payloads that lack a session ID. The plugin must still account for a Hermes tool call that fails after a pre-execution reservation. No LifeOS source file was changed by this probe.
