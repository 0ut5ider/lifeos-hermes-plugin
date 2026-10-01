# Memory background review

Date: 2026-09-30

Role: Independent bounded code and behavior reviewer

Question: Does actual background skill review use generated-content admission without weakening model routes, identity, primary-user protection, or thread isolation?

Model: GPT-6. The exact model variant is not exposed in this agent context.

## Result

**The five background-review cases pass independently, but I confirmed a high-priority foreground continuation defect.** A second ordinary foreground turn fails before its model request because its new admitted input proof does not replace the calling thread's previous bound proof. The same failure occurs without background review.

This is an existing input-proof handoff defect exposed by the requested continuation probe, not observed leakage of the background-review origin. The primary has confirmed the diagnosis and is preparing a fix. This report preserves the reviewed initial state; it does not review that subsequent fix.

The full requested focused suite passed **76 tests in 181.390 seconds**, no failures or skips. The tests currently miss the failing second-foreground-turn case.

## Confirmed finding: ordinary next foreground turn retains the previous input proof

Priority: high, functional failure of ordinary conversation continuation.

Location: `memory_runtime.py`, the worker admission to parent `_BOUND` handoff and `_check_call` stamp comparison.

### Actual foreground-after-review reproduction

The review-only child helper runs these real operations in one AIAgent process:

1. Run an approved foreground turn.
2. Spawn the actual background review thread.
3. Execute its real skill_manage tool call and create the native SKILL.md file.
4. Wait for the review thread to finish.
5. Run another foreground turn with a different original human message and the actual previous conversation history.

The first foreground turn and review succeed, producing three HTTP completions. The parent origin remains `assistant_tool`, not `background_review`. The following foreground turn makes no fourth HTTP request. It fails after three host attempts with an invalidated-memory-context error.

Reproduction: `raw/probe_foreground_after_review.py`. Exact child: `raw/foreground_after_review_child.py`. Full result and failed assertion: `raw/foreground-after-review.txt`.

The follow-up message deliberately quotes a previously forgotten synthetic fact. It is a new human-authored quote, which the established primary-input exception should preserve. The admission generation was already current before the first turn; no native fact changes occur between turns.

### No-review control and measured cause

The paired control disables background review and runs the same first and second foreground turns. It reproduces the failure:

```text
review_done: null
foreground origin: assistant_tool
first foreground failed: false
second foreground failed: true
HTTP completions: 1
```

The child then reads its actual thread binding and persisted session admission. They differ in exactly one field:

| Stamp field | Calling-thread binding | Persisted admission |
| --- | --- | --- |
| user_input | Original text proof, length 24 | Newly admitted text proof, length 45 |
| scope | Equal | Equal |
| generation | Equal | Equal |
| rendered | Equal | Equal |
| context | Equal | Equal |

The host runs pre-prompt admission in a worker. Successful admission publishes the new turn's proof, but the parent still has an existing bound tuple, so the model guard does not reconstruct it from the new admission. Its comparison rejects the otherwise valid next turn.

Evidence: `raw/probe_foreground_without_review.py`, `raw/foreground_without_review.txt`, and compact `raw/proof-difference.json`.

The no-review probe exits zero because it explicitly asserts the observed defect while recording it. The original after-review probe exits one because it expected a successful follow-up. These statuses do not indicate that the feature passed.

Correction direction: propagate or securely rebind the verified per-turn admission in the calling thread. Preserve the existing identity, scope, generation, installed-prompt, and original-input verification checks. Add a real two-turn regression with and without background review. The primary will implement and request closure.

## Background-review implementation findings

The production change reads the already loaded host `tools.skill_provenance` module and its `is_background_review()` value. It does not set or reset that value. A background fork is classified as generated input, which removes the human-input proof exemption and disables primary history projection. All existing ownership, identity, destination, route, generation, and required final checks remain in the same path.

The host provenance value is a ContextVar. The review thread runs inside a copied context, and turn setup assigns the fork's background-review origin. The parent continuation probe observes `assistant_tool` after the thread finishes. I found no origin-marker leakage or new permission exemption in this change.

## Independent background results and actual artifacts

I ran the requested unittest command and separately executed the primary's capture_after.py unchanged. Its five cases use the real foreground agent, real background fork and thread, actual skill_manage, and native skill approval storage against a scripted localhost model endpoint.

| Case | Actual completions | Result |
| --- | ---: | --- |
| Direct background skill creation | 3 | Exact expected SKILL.md exists, no pending skill request, action summary published. |
| Skill approval enabled | 3 | No live skill file; one native pending record with origin background_review and exact operation content. |
| Retired generated review focus | 1, foreground only | No review completion or skill file. |
| Unapproved review model | 1, foreground only | No unapproved model completion or skill file. |
| Retired foreground quote inherited by review | 1, foreground only | Foreground quote allowed; review sends no completion and writes no skill. |

The preserved MEMORY.md and USER.md bytes remain unchanged. Their markers do not enter the direct skill-creation requests. The capture includes wire bodies, actual skill files, pending records, summaries, and diagnostics in `raw/capture-after.txt`.

The thread join is justified: request_done signals completion of provider-capable work before summary publication. Joining the actual bg-review thread makes the summary assertion deterministic in this isolated process. The fixture's /api/show allowance accepts only the configured foreground or review model names; it does not permit unapproved generation requests.

The denied cases assert observable absence of model completions and skill files. Their captured review summaries and diagnostics are empty. They do not expose the fork's exact internal denial reason as a separate asserted result; the reviewed guard ordering and allowed controls support the intended interpretation.

## Focused regression gate

| Module | Tests |
| --- | ---: |
| test_memory_review | 5 |
| test_memory_agent | 6 |
| test_memory_host | 4 |
| test_memory_runtime | 25 |
| test_memory_history | 16 |
| test_memory_model_calls | 13 |
| test_hermes_memory_provider | 7 |
| Total | 76 |

All passed. Full stdout/stderr: `raw/tests.txt`. The background capture is another execution of the five review cases, not five additional distinct tests.

## Source, original failures, and safety

Base HEAD is 2879605 on feature/lifeos-memory. Exact initial snapshots, reviewed diff and SHA-256 hashes are saved under raw/. Host snapshots cover provenance, context propagation, review lifecycle and turn setup. `raw/source-changes.json` records later changes, including the primary's explanatory comment when applicable. Subsequent fixes are not silently treated as the tested initial snapshot.

The primary's instrumentation failure and original before probe are preserved with a primary- prefix. I do not count those supplied results as independent executions. The original failed continuation probe is preserved with its complete outcome and assertion traceback.

All runs use the complete memory-plugin-test-env Python with explicit owned app-startup source paths and private synthetic profiles. No implementation edits, commits, push, live-system imports/bootstrap, SSH, account changes, or memory/journal calls occurred. Exact commands are in `raw/commands.txt`.

## Scope and next review

This unit exercises an explicitly spawned real background review after a foreground turn. It does not verify the full automatic cadence, idle queue, concurrent foreground cancellation/requeue, native automatic extraction, or delivery lifecycle. The model endpoint follows a deterministic script; it does not test model judgment about which skill to learn.

Resume repair, changed SOUL repair, compression rotation, Responses repair, restricted prompts, delivery, and ownership activation remain open. Ordinary foreground continuation is not resume repair and must be fixed and reviewed before this unit is considered closed.
