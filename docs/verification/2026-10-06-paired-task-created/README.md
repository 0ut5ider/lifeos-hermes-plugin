# Paired task creation

Date: 2026-10-06. Two cases create one task in Claude Code 2.1.272 (`TaskCreate`) and Hermes (`todo_list`). TaskGovernance runs on `TaskCreated.1.1`. Both clients pass in the paired runtime on the development container.

| Case | Description | Effect on both clients |
| --- | --- | --- |
| `generic-task-allow` | `Write the synthetic pair fixture report.` | Hook exit 0, no output, no LifeOS file change, no block message in a later model request |
| `generic-task-block` | `Short` | Hook exit 2, no stdout, no LifeOS file change, the block message `Task creation blocked: description too short` reaches the next model request |

[task-proof.json](task-proof.json) recomputes these effects from the raw captures and checks that each hook receives the requested description. [runtime-check.json](runtime-check.json) verifies the runtime sources.

## Setup differences

- Claude Code 2.1.272 exposes `TaskCreate` only for a Haiku model identity. The native client requests `claude-haiku-4-5`; the relay answers with the private model, as for every other case.
- The bridge runs the native task hook only when its command is the literal installed `bun <root>/hooks/TaskGovernance.hook.ts` and the capability record matches. The fixture therefore installs the hook and, on the Hermes side, the capability record under the fixture root. A tracing `bun` program first on `PATH` records each run on both clients.
- A Hermes todo item has one text field. The Hermes prompt asks for a todo whose content is exactly the description; the native prompt gives a subject and a description. In an earlier run, the Hermes model wrote `PAIR_TASK: Short` as the content, which passes the 10-character rule.
- Each client runs its own program: the native reference keeps the upstream TaskGovernance, and Hermes uses the patched version that accepts the bridge session count. Native writes its count to `/tmp`, which the fixture isolates. The bridge keeps its count in `LIFEOS/MEMORY/STATE/hermes-task-counts`, which the comparison excludes like its transcripts.
- Hermes discovers the todo tool through `tool_search` before it calls it, so its model request count is model-chosen.

## Limits

These cases do not cover the 50-task session limit, kanban tasks, or a task created inside a delegated child. The focused gate passes 116 tests.
