# Memory background review closure

Date: 2026-09-30

Role: Independent bounded closure reviewer

Question: Does verified per-turn input rebinding restore ordinary foreground continuation without weakening model admission or background isolation?

Model: GPT-6. The exact model variant is not exposed in this agent context.

## Conclusion

**The ordinary foreground continuation finding is closed for the reviewed scope. No further material defect found.**

The unchanged archived child now completes a foreground turn, real background review and skill write, then a successful quoted follow-up in the same AIAgent process. The parent origin remains assistant_tool. The full focused suite passed **81 tests in 195.043 seconds**, with no failures or skips.

Ten additional targeted handoff scenarios verified that new input proofs do not grant changed identities, routes, policies, prompts, missing state, or inactive ownership. Denied requests leave the calling-thread binding unchanged. The reviewed source hashes remained stable through final verification.

## Fix inspected

The primary execution path now rereads the persisted session stamp under the cooperating native transaction and can adopt its non-null input proof only when prior scope, generation, rendered prompt, and context fields agree. The normal current-state comparison remains in place after that provisional local adoption.

Request projection verifies the current primary input against the admitted proof. The implementation publishes the calling thread's ContextVar binding only after the checks complete successfully. Auxiliary calls and direct final admission checks cannot use this primary handoff path.

The native generation-refresh checks remain separate: a safe fact-only refresh can still project retired content, while changes in permission, identity or installed prompt remain refused. Inspection and targeted cases found no new bypass in the tested chat-message handoff.

## Original archived reproduction, now successful

I ran the saved foreground_after_review_child.py byte-for-byte. The driver is the primary's rerun_archived_continuation.py with only its evidence directory changed. It does not regenerate the child from the updated shared helper. `raw/archived-child-hashes.json` confirms the executed copy equals the original.

Observed result:

```text
child process returncode: 0
stderr: empty
foreground origin after review: assistant_tool
review_done: true
follow-up failed: false
follow-up final response: SYNTHETIC-FOREGROUND-OK
actual HTTP completions: 4
```

The real review creates the exact expected SKILL.md and publishes its action summary. The fourth request contains the newly authored human quote. Both original built-in memory files remain byte-identical. This closes the original failure using the same child program and actual host/model/tool path.

Full request and outcome evidence: `raw/archived-continuation.txt`. Driver: `raw/rerun_archived_continuation.py`. Exact executed child: `raw/archived_after_review_child.py`.

## Targeted handoff checks

`raw/probe_handoff_guards.py` uses actual thread-pool admissions, native fixture operations, configuration updates and persisted context state. It does not replace policy or implementation methods. These are runtime boundary probes, separate from the archived full HTTP-agent reproduction.

| Scenario | Result |
| --- | --- |
| Correct newly admitted primary input | Dispatched and verified by final admission. |
| Previous input borrowing the next turn's proof | Denied; binding unchanged. |
| extra_body selects an unapproved model | Denied; binding unchanged. |
| Authenticated author changes | Denied; binding unchanged. |
| Configuration policy changes | Denied; binding unchanged. |
| Installed SOUL changes | Denied; binding unchanged. |
| Persisted session admission is lost | Denied; binding unchanged. |
| Ownership becomes inactive | Denied; binding unchanged. |
| A third worker admission supersedes the second | Older input denied with unchanged binding; the newest verified input succeeds. |
| Input handoff plus a native forget | Succeeds only after projecting the retired assistant content; final admission accepts the projected request. |

Exact output is `raw/handoff-guards.txt`. For the third-input case, the initial dispatch count records denial of the older request. The separate latest_admitted_input_dispatches field records the subsequent successful newest-input control.

The focused suite also reruns the controlled concurrent-session admission regression: a repair cannot overwrite another session's newly published state, and inactive retained lineage remains denied.

## Independent focused suite

| Module | Tests | Result |
| --- | ---: | --- |
| test_memory_review | 7 | Passed |
| test_memory_agent | 6 | Passed |
| test_memory_host | 4 | Passed |
| test_memory_runtime | 25 | Passed |
| test_memory_history | 19 | Passed |
| test_memory_model_calls | 13 | Passed |
| test_hermes_memory_provider | 7 | Passed |
| Total | 81 | Passed |

The new real two-turn tests cover ordinary continuation both with and without background review. Worker-handoff cases cover verified current proof, mismatched current input, and refusal to rebind auxiliary or direct final checks.

The remaining gate preserves background skill creation and approval staging, denied review routes, retired generated-input refusal, actual native recall correction/forget turns, protocol/transcript preservation, model-request overrides, and the earlier SDK admission regressions. Full stdout/stderr is `raw/tests.txt`.

## Evidence and source integrity

Reviewed production and test snapshots and their SHA-256 hashes are in `raw/source-hashes.json` and adjacent files. The post-test comparison found no drift; `raw/source-changes.json` is empty. The original report and failed reproduction artifacts remain unchanged.

Exact commands are in `raw/commands.txt`. They use the complete memory-plugin-test-env Python, PYTHONPATH=.:tests, and explicit owned app-startup Hermes and LifeOS sources. All profiles, native facts, configuration changes, skill writes and HTTP endpoints were synthetic fixtures.

No implementation edits, commits, push, live-system imports/bootstrap, SSH, account changes, or memory/journal calls occurred. The only review-created repository files are evidence and probe artifacts.

## Remaining scope and review priorities

This verifies ordinary live-agent foreground continuation and the bounded explicitly spawned background review. It does not prove all automatic review cadence, idle queue, cancellation/requeue, or delivery behavior. The localhost endpoint returns scripted responses, so this is integration evidence rather than an evaluation of model skill-learning judgment.

Resume repair, changed installed SOUL repair, compression rotation, Responses repair, restricted prompts, delivery, and ownership activation remain open. The prompt-change probe verifies refusal, not automatic prompt repair. The direct admission and auxiliary refusal checks do not add repair support to those paths.

No further fix is requested for the bounded finding reviewed here. The remaining gates retain their separate verification requirements.
