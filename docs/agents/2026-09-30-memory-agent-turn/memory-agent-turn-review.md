# Memory agent turn review

Date: 2026-09-30

Role: Independent bounded code and behavior reviewer

Question: Does the complete agent-turn fixture exercise real governed tool execution, native persistence, authenticated writer identity, receipt propagation, and denial before model access?

Model: GPT-6. The exact model variant is not exposed in this agent context.

## Conclusion

**No material finding in the reviewed unit.** The independent focused run passed all 16 tests. The additional native-record probe also passed. This closes the bounded explicit tool-turn and unknown-author characterization against the reviewed source snapshot.

The fixture uses a scripted localhost model endpoint. The host agent, plugin loading, prompt admission, SDK request path, tool dispatcher, memory service, and native persistence are real. The endpoint requests a tool and constructs its final reply from the tool result actually returned by the host. It does not manufacture the committed reference or call the memory implementation itself.

This evidence supports integration correctness for one explicit remember turn. It does not establish real-model reasoning quality, native automatic recall, complete session lifecycle, compression rotation, delivery, or activation readiness.

## Reviewed source

Repository: `/home/outsider/Projects/Hermes_agent/LifeOS_plugin`, branch `feature/lifeos-memory`, base HEAD `5dbe2b7`.

Reviewed changes:

- `tests/memory_host_calls.py`: optional real `AIAgent.run_conversation` invocation and authenticated-author fixture parameter.
- `tests/test_memory_host.py`: conversation settings and request classification while preserving constructor-only assertions.
- `tests/test_memory_model_calls.py`: optional local endpoint response callback, used only for chat completions.
- `tests/test_memory_agent.py`: allowed tool turn and rejected unknown author.

I inspected the corresponding installed-plugin provider and admission code and the prepared host conversation loop, model middleware invocation, and provider-tool dispatch. No implementation changed in this unit or during my review. Source hashes, test snapshots, reviewed diff, and relevant host snapshots are saved under `raw/`. The final hash check found no drift.

## Independent results

| Check | Result |
| --- | --- |
| Complete allowed agent turn | Passed. Two `/v1/chat/completions` requests; actual native save; committed receipt in final response. |
| Unknown author | Passed. `prompt_blocked`, zero API calls, zero observed HTTP requests, no matching native fact. |
| Constructor and ownership regression tests | All 4 passed. |
| SDK and retained-prompt fixture regressions | All 10 passed. |
| Additional persisted-writer probe | Passed. Native record contains writer `chat-a:100`, category `project`, project `lab`, and the expected exact content. |

Focused gate: **16 tests passed in 78.476 seconds**, no failures or skips. Full output is `raw/tests.txt`. The evidence runner calls the unchanged unittest methods. It only saves successful tests' output and wire captures.

### Allowed turn, actual flow

1. A fresh subprocess imports the owned prepared host with private HOME and HERMES_HOME and an installed plugin copy.
2. It constructs the real AIAgent and runs `run_conversation` under the synthetic approved account `chat-a:100`.
3. The local endpoint receives the first real SDK request and returns a `lifeos_memory_remember` tool call for the synthetic `lab` project.
4. The host dispatches the tool through its actual memory manager and LifeOS provider. The provider uses the admitted account context.
5. The native backend commits the requested fact and returns its receipt.
6. The second actual HTTP request includes that tool receipt. The endpoint copies the receipt's status, reference, and writer into its final assistant message.
7. The test resolves the returned reference through native-backed `memory.get` and verifies the exact saved content.

Both original built-in file markers are absent from both actual model-request bodies. The shared fixture checks that MEMORY.md and USER.md remain byte-identical. The additional probe confirms the stored writer and project directly, rather than relying only on the final receipt.

The independent wire capture records an allowed turn with `completed=true`, `failed=false`, two API calls, and final receipt writer `chat-a:100`. The receipt has a newly generated record ID and revision 1. Full synthetic requests and outcomes are retained in `raw/test_actual_agent_turn_commits_native_fact_and_reports_its_receipt.txt` and `raw/persisted-writer.txt`.

### Denied turn, actual flow

The denied author's admission fails in the actual pre-prompt callback. The real host reports `turn_exit_reason=prompt_blocked`, `api_calls=0`, `completed=true`, and `failed=false`. The final text names the missing approved identity binding. My capture contains no HTTP requests at all. The native recall assertion finds no matching denied fact.

The host intentionally classifies a prompt block as a completed handling outcome. The earlier assertion that `failed` must be true was incorrect. Its original failure output is preserved separately as `raw/primary-memory-agent-denied.txt`. The current test correctly asserts the explicit block reason and absence of side effects.

## Test claims and limits

- The endpoint supplies deterministic model responses. It tests the full integration path but does not measure whether a real model would choose the right tool or faithfully summarize a receipt.
- The allowed test proves native content and receipt writer. My additional probe independently verifies the writer stored with the native record. The tool arguments do not provide that writer.
- The denied test's local model would return ordinary text if reached. The zero-call assertions are therefore essential and present. Its lack-of-fact assertion alone would be insufficient to establish denial.
- The prepared host invokes required LLM admission middleware on the real request path. This new pair of tests does not independently prove every possible middleware failure or route-change case; the 10 existing SDK tests were rerun because their server fixture changed.
- A successful native save and receipt propagation exercise admitted context across the model and tool path. They do not establish a full audit of all tools or external model clients.
- The fixture settings contain no native automatic recall configuration. It therefore makes no automatic recall claim.
- `skip_context_files=True` and `skip_background_review=True` remain deliberate fixture constraints. User-supplied context, background review, retained-history rebuilds, compression rotation, and post-turn delivery are not covered.
- Each run uses a fresh synthetic profile. This is not an ownership activation transaction, installer recovery test, or live production validation.

## Commands and artifacts

Complete commands are in `raw/commands.txt`. The independent suite uses `/home/outsider/.cache/lifeos-plugin-memory/memory-plugin-test-env/bin/python` and explicitly selects both prepared app-startup host and LifeOS sources. The runner and persisted-writer probe are retained as executable Python source in `raw/`.

The parent-reported minimum-context fixture adjustment to 131072 tokens is consistent with the current fixture and the successful run. I did not reproduce that earlier configuration error. Parent gate output, when available, is retained separately and is not counted as independent evidence.

## What deserves Adrian's review

The remaining distinction is between a complete explicit tool turn and the wider memory lifecycle. This unit verifies the former. Automatic sources, lifecycle transitions, history or compression repair, delivery boundaries, and ownership activation still need their own evidence. I made no implementation edits or commits and accessed no live server, account, memory, or journal. All runtime changes were confined to disposable synthetic fixtures.
