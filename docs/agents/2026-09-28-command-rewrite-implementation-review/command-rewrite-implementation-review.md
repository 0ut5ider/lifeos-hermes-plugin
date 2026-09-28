Date: 2026-09-28
Agent role: Read-only implementation reviewer
Question: Does the Hermes command rewrite patch preserve safety, approval, and audit correctness?
Model: GPT-6 Codex (inherited model)

Reviewed the working diff on lifeos-hermes@192.168.8.212:~/workspace/hermes-agent, based on 48f0a3d12d5a, and the matching local patches/hermes-command-rewrite.patch. No source edits were made.

Blocking findings

1. High: review decisions discard mandatory rewrites and skip validation.

In tools/approval.py _plugin_command_decision, the review branch precedes replacement collection and validation. With plugin results [{action: review}, {action: rewrite, command: B}], the function returns review for A. If the user approves, the terminal executes A. The rewrite plugin never authorized A as the final command. With review plus empty or conflicting rewrites, the function still returns review, contrary to the intended fail-closed contract. The AST-extracted production function reproduced all three cases. See probe-output.json.

Fix by validating replacements before reducing review decisions. Preserve both replacement and review requirements, or conservatively deny a combination that cannot be represented. A simple swap of branch order is insufficient if the review requirement then disappears: review must remain effective for the final command, or the relevant plugin must evaluate that command again before execution.

2. High for audit parity: effective input mutation does not cross argument coercion.

The new _effective_args argument mutates the dictionary received by _handle_terminal. However normal agent execution calls model_tools.handle_function_call, which calls coerce_tool_args. That function calls unrename_tool_args, which always constructs a new dictionary for the terminal schema. Therefore the registry dictionary changes while the executor dictionary remains A. The agent suppresses the inner post_tool_call and later emits its own post_tool_call with the unchanged outer _ToolCallRef.args. The executed command is B, but the native PostToolUse hook and outer result audit see A.

The added test calls _handle_terminal directly, bypassing coercion and the executor. Its args assertion does not establish real audit behavior. The extracted real unrename_tool_args function confirms distinct dictionaries and the stale original after mutation. See probe-output.json and source excerpts. Carry effective arguments through a supported dispatch return/context mechanism or explicitly propagate them across coercion, then test the normal executor observer path.

Other limitations and test gaps

- The effective arguments update occurs only after final successful approval. A replacement rejected by a hardline, plugin, pre-exec guard, or pending human approval still reports A in failure observers. Decide and test whether failure hooks should receive the candidate B that was refused.
- The implementation correctly loops through terminal pre-exec guards and the full command guard for each replacement, so ordinary execution cannot run B solely on approval of A. The changed command also receives foreground/background guidance validation and PTY detection. Explicit deny wins before rewrite. Malformed/conflicting rewrites without review and cycles fail closed.
- Prepared batch results are consumed under the original argument identity and return a replacement directive. The next loop pass checks B without a matching cached result, so B is checked live. This structure avoids a direct cached-original-to-unchecked-replacement bypass. A regression test should still cover prepared approval consumption and changed workspace/task/call, since none of the added tests exercise it.
- force=True remains an internal bypass that does not invoke rewrite hooks. The inspected production paths did not reveal an active terminal replay caller passing force=True. Do not claim gateway replay coverage without an explicit test that pending approval records B and continuation executes B.
- No added test covers replacement-specific user-deny, sudo stdin, runtime self-delete, Tirith, pending review, smart approval, session approval fingerprints, isolated container behavior, pre-exec denial/timeout, same-command termination, or replacement-limit exhaustion.
- The background test replaces spawn_background_process with a stub. It verifies argument dispatch but does not demonstrate real background execution or resulting audit input.
- check_all_command_guards now returns approved=True with replacement_command before checking the replacement. Current terminal flow treats that as an intermediate directive. Its public docstring still calls the result a final approval decision. Document this contract explicitly so future callers cannot mistake it for approval of the original or replacement command.

Validation and limits

Executed two source-level probes without changing the remote checkout. Probe code is saved as probe.py and results as probe-output.json. These execute extracted production functions with minimal isolated dependencies; they are unit probes, not end-to-end tests.

Attempted the added pytest file using ~/workspace/hermes-test-venv/bin/python. Collection failed because ruamel.yaml is unavailable there:
ModuleNotFoundError: No module named 'ruamel'

Attempted the managed Hermes launcher with --run-module pytest. It failed because that runtime lacks pytest:
ImportError: No module named pytest

Those two attempts were test environment failures. After the parent supplied the established PYTHONPATH to the managed runtime site-packages, the focused file passed: 35 passed in 2.86s. The output is saved in focused-tests.txt. The passing tests do not cover the two blocking findings above. host-diff-and-audit-source.txt preserves the reviewed diff and key audit source.
