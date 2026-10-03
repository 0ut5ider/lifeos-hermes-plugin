# Review observations and command record

Date: 2026-10-01. Role: independent design reviewer. Model: GPT-6.1-Sol (`gpt-6.1-sol`), high reasoning effort. The delegating agent supplies the runtime identity.

Working directory for substantive inspection: `/home/outsider/Projects/Hermes_agent/LifeOS_plugin`.

The review used read-only source inspection. No behavioral experiment or test suite ran. No model, live server, memory, or journal endpoint was called. Commands performed Git state reads, `cat`, `rg`, `nl`, `sed`, and Python source copying/hashing. `apply_patch` wrote review artifacts only.

## Initial exact commands

```sh
cat /home/outsider/.agents/skills/coding-rules/SKILL.md
git status --short; git branch --show-current; git rev-parse HEAD
rg --files -g AGENTS.md -g '*memory*' -g '*adopt*' -g '*preferences*' -g '*registry*' -g '*journal*' notes docs lifeos_hook_bridge tests
nl -ba notes/2026-09-30-memory-design.md
nl -ba docs/memory-implementation-plan.md
nl -ba notes/2026-09-30-memory-host-ownership.md
```

The initial Git read returned a clean tree, branch `feature/lifeos-memory`, and HEAD `d8b4ae5e399437bf5fe2a203e5065190c06eef7f`. Large initial discovery output was truncated in the tool response. Later numbered full source snapshots retain the actual reviewed files.

An initial source-copy Python command accidentally used the default `messaging` working directory. It failed on the first source lookup with `FileNotFoundError`, after creating an empty review/raw directory. Two relative-path inspection commands also failed there. The next command removed the two empty mistakenly created leaf directories with `rmdir` and reran source copying with the explicit correct working directory. No source file was read or changed by this failed attempt. No file was written in `messaging`.

A Python ancestor walk checked project and ancestor `AGENTS.md` paths. It printed no project-specific instruction file. The supplied shared AGENTS.md instructions governed the review.

## Retained inspection command output

`inspection-batch.json`, `inspection2.json`, `inspection3.json`, `inspection4.json`, `inspection5.json`, and `inspection6.json` each store exact shell commands, exit codes, stdout, stderr, and tool results. Some broad `rg` output is explicitly marked truncated. The report relies on later focused commands and full numbered snapshots for citations.

Two guessed paths were absent: `hermes/agent/initialization.py` and `hermes/tools/memory_store.py`. Their error output remains in inspection4/inspection5. The actual sources are `agent/agent_init.py` and `tools/memory_tool_store.py`. The imports in `tools/memory_tool.py:43-44` identify the latter. A final grep of `hermes_cli/web_server_memory.py` returned no matching graph/store/flag lines; it does not establish endpoint behavior.

Additional exact focused commands, whose source output is retained in the numbered snapshots:

```sh
rg -n 'class MemoryStore|def freeze_snapshot|MEMORY.md|USER.md' /home/outsider/.cache/lifeos-plugin-memory/source-gate-20261001-cortex-final/hermes/agent /home/outsider/.cache/lifeos-plugin-memory/source-gate-20261001-cortex-final/hermes/tools/memory_tool.py | head -65
rg -n 'profiles|configuration|HERMES_HOME|get_hermes_home|root|memory-provider|provider' lifeos_hook_bridge/memory_provider.py | head -85
sed -n '1,80p' /home/outsider/.cache/lifeos-plugin-memory/source-gate-20261001-cortex-final/hermes/tools/memory_tool.py
rg --files /home/outsider/.cache/lifeos-plugin-memory/source-gate-20261001-cortex-final/hermes | rg '/memory_store|memory_store.py|memory.py$'
nl -ba /home/outsider/.cache/lifeos-plugin-memory/source-gate-20261001-cortex-final/hermes/tools/memory_tool_store.py | sed -n '130,210p;485,535p'
rg -n 'target_kind|identity|proposal|hot' lifeos_hook_bridge/memory_proposals.py | head -65
nl -ba /home/outsider/.cache/lifeos-plugin-memory/source-gate-20261001-cortex-final/lifeos/LifeOS/install/LIFEOS/TOOLS/MemorySystem.ts | sed -n '679,745p'
nl -ba /home/outsider/.cache/lifeos-plugin-memory/source-gate-20261001-cortex-final/hermes/tools/memory_tool_store.py | sed -n '18,88p'
```

## Source-copy operation

The snapshot script read each specified source with `Path.read_text()`, enumerated `splitlines()` starting at line 1, and wrote `f'{i:6}\t{line}\n'` for each line. These are citation copies rather than byte-identical backups. `source-identities.json` records SHA-256 computed from `Path.read_bytes()` and maps prepared source paths to numbered snapshots. Initial repository source copies include the design, progress, ownership and adoption notes, adoption/preferences/policy/provider/service/native/transaction modules, and focused adoption/preferences tests. Later copies include access/proposals, host tool/store/agent-init/graph/mutations/manager/system-prompt, and native MemoryWriter/MemorySystem sources.

The primary independently verified source claims and added `primary-source-verification.json`. That file is preserved unchanged. Its verification is separate from the reviewer's inspection and does not represent test execution.

## Concrete observations

1. Native adoption creates metadata references to existing LifeOS content. It does not write source facts or select Hermes entries.
2. Policy categories are project, principal, assistant. Governed native add supports memory, knowledge, idea, proposal. Native discovery/adoption recognizes existing learning notes.
3. Original-source metadata is limited to source kind/session, writer, target path and update time. A proposed source-file/date/span import linkage is not implemented.
4. Permissions apply by category, project, and private entity path. Existing grants can expose newly published accepted content without any new enrollment.
5. Native retry and recovery are per governed operation. They do not atomically encompass a Hermes backup, profile settings, provider selection, two flags, and a multi-item import.
6. Hermes uses the full newline-section-sign-newline delimiter and strict UTF-8-with-BOM handling. Read-only parsing can hide read failure as an empty list.
7. Hermes stores source snapshots at load time and can reuse a session's external manager across fresh agents.
8. The prepared learning graph reads preserved source files without checking built-in flags. Its mutation path calls `_mutate`, whose implementation does not check those flags. This is static evidence, with no claim of an executed browser exploit.
9. Native hot writer caps and complete readback checks support explicit preflight and loss detection. They do not authorize unreviewed eviction or create private archive/learning routes automatically.
10. Configured ownership activation remains gated. A successful preferences health call is not an accepted-fact retrieval or session handoff test.

All acceptance cases in `memory-import-review.md` are proposed future tests. None are reported as passed.
