# Hermes background skill review

Date: 2026-09-30. All profile contents, identities, skills, and HTTP responses are synthetic.

## Sources and command

Hermes base: `758ad514eb0e800547e015edf05aa18f78b78d82`, with the distributed compatibility patches. LifeOS base: `5e2f2e8c0abde612da0e99c16c0d07d4ec21b88c`, with the distributed native access patch. Prepared sources are under `~/.cache/lifeos-plugin-memory/source-gate-20260930-app-startup/`.

The complete interpreter is `~/.cache/lifeos-plugin-memory/memory-plugin-test-env/bin/python`. Set `LIFEOS_MEMORY_SOURCE` and `LIFEOS_HERMES_SOURCE` to the prepared installation directories. Set `PYTHONPATH=.:tests` from the plugin repository.

```sh
python -m unittest test_memory_review test_memory_agent test_memory_host test_memory_runtime test_memory_history test_memory_model_calls test_hermes_memory_provider -v
python docs/verification/2026-09-30-memory-background-review/capture_after.py
```

The child imports the prepared Hermes source, creates a real `AIAgent`, and runs a foreground turn. It starts Hermes's actual review thread. The endpoint returns scripted model messages. The host performs the requested skill operation through its actual tool dispatch. There are no mocked admission, native persistence, skill guards, approval gates, or review threads.

## Before the fix

`capture_before.py` is the original observational probe. `probe-before.txt` records one foreground HTTP request and zero review requests. Tracing captures the actual review result: `Memory history cannot verify the current user input`. The background user-role prompt cannot match the inherited foreground input proof. `before.txt` records both expected positive-case failures before the fix. That initial test command also discovers four imported fixture tests; the current test module imports the fixture module instead.

## Required outcomes

| Case | Foreground calls | Review calls | Files |
| --- | --- | --- | --- |
| Automatic skill review | 1 | 2 | The native skill file contains the requested instructions. |
| Explicit review with approval | 1 | 2 | The native pending record contains the requested instructions. No skill file exists. |
| Forgotten generated focus | 1 | 0 | No skill file exists. |
| Forgotten original human quote | 1 | 0 | The foreground quote is allowed. The review cannot reuse the quote. |
| Unapproved review model | 1 | 0 | No skill file exists. |

`wire-after.json` records the actual HTTP bodies, outcomes, skill files, curator ledger, pending records, and both preserved built-in files for all five cases. The review model may perform its ordinary `/api/show` metadata probe before admission. That probe does not contain private facts; it does not establish model-call permission.

The fixture waits for the review request event and joins the actual `bg-review` thread before collecting output. The request event precedes summary publication. An event-only wait allowed the summary to race the fixture's JSON output. This was a fixture synchronization error, not a failed skill write.

## Limits

These tests establish execution of the automatic and explicit review fork paths. They do not prove a real model chooses an appropriate skill, every nudge schedule, reviewer route, curator job, or profile transition. Required memory checks can still refuse stale generated history. Automatic rebuilding of that review history remains open. The change adds no Hermes or LifeOS patch. It does not activate lasting-memory ownership on a running installation.

## Independent continuation finding

The reviewer runs a second ordinary foreground turn after a successful review. The parent origin remains `assistant_tool`, but the model request fails. A no-review control fails in the same way. Persisted admission and the calling-thread binding differ only in the user-input proof. `continuation-before.txt` is the primary reproduction. `continuation-tests-before.txt` records the two failing real-agent cases and the failing worker-handoff case before the fix.

The next fix rebinds only the new worker proof in primary execution, with identical scope, generation, rendered prompt, and context. History projection must verify that the actual current user input matches that proof. Auxiliary requests and direct final checks cannot rebind it. The change does not refresh revoked policy or reconstruct changed installed prompts.

`rerun_archived_continuation.py` runs the reviewer's unchanged archived child against the current plugin. The original probe constructs its child from the current shared helper. That helper now contains follow-up support, so regenerating the child would duplicate its follow-up. Running the archived child preserves the original reproduction.

`full-before-continuation-fix.txt` executes 617 cases: 540 pass and 77 skip. It starts before the continuation fix, with its cases already collected before the continuation tests were added. It is not closure evidence for that fix.
