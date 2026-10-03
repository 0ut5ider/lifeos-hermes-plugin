# Memory conversation repair evidence

Date: 2026-09-30. All facts, identities, model responses, and endpoints are synthetic. No running installation changes ownership.

## Fixture

The prepared Hermes base is `758ad514eb0e800547e015edf05aa18f78b78d82`. The prepared LifeOS base is `5e2f2e8c0abde612da0e99c16c0d07d4ec21b88c`. Both trees use the distributed patches in `~/.cache/lifeos-plugin-memory/source-gate-20260930-app-startup/`. This unit adds no host or native source patch.

The interpreter is `~/.cache/lifeos-plugin-memory/memory-plugin-test-env/bin/python`. Set `LIFEOS_HERMES_SOURCE` to the fixture's `hermes` directory, `LIFEOS_MEMORY_SOURCE` to `lifeos/LifeOS/install`, and `PYTHONPATH=.:tests`. Native subprocesses use the existing Bun dependencies with automatic installation disabled.

## Recorded results

| Artifact | Meaning |
| --- | --- |
| `capture-before.txt` | Native changes commit, but the third model request is refused three times. Host diagnostics also break the initial fixture JSON parser. |
| `capture-before-structured.txt` | The corrected fixture separately captures the actual failed-turn result and diagnostics. Both operations still fail to confirm their committed change. |
| `agent-tests.txt` | Four initial complete agent tests pass after request projection. Native hook recall is not configured in this run. |
| `native-recall-before.txt` | Two real LoadMemory cases fail because the current user role still contains appended old recall. |
| `agent-closure.txt` | All six complete agent tests pass after original-input binding, including actual native recall. |
| `closure-primary.txt` | The first corrected focused gate passes 66 cases. It does not include the later auxiliary-proof regression. |
| `state-race-primary.txt` | The unchanged review probe retains concurrent admission and refuses its inactive retained lineage. Its final assertion expects the old defect. |
| `proof-compression-primary.txt` | The unchanged archived child passes primary and summary controls with clean output and one HTTP request each. |
| `second-closure-primary.txt` | The focused gate passes 68 cases, including the auxiliary original-input regression. |
| `aux-responses-primary.txt` | The unchanged Responses probe permits the primary quote and refuses `memory_review` before transport. |
| `instructions-before.txt` | A real SDK test fails because escaped JSON in instructions reaches the endpoint. |
| `third-closure-primary.txt` | The corrected focused gate passes 71 cases without failures or skips. |
| `rerun_archived-primary.txt` | The primary reruns unchanged archived children and verifies accepted and denied transport outcomes. |
| `probe_allowed_responses-primary.txt` | Clean JSON instructions and clean auxiliary Responses string input each send one successful request. |
| `turns-primary.txt` | Six actual agent outcomes and HTTP captures from the primary evidence runner. |

The original-input proof stores no user-message body. It binds the length, input kind, and SHA-256 hash. The provider preserves transcripts and the existing disabled Hermes memory files. Tool call IDs remain stable, and successful mutation receipts remain available in the next model request.

The final independent closure passes 71 tests without failures or skips and finds no further material defect in this bounded unit. Its source hashes match the primary checkout. The primary reruns its archived and accepted-control probes successfully. The report is `docs/agents/2026-09-30-memory-history-repair/third-closure/memory-history-repair-third-closure.md`.

## Limits

This unit repairs retained chat content inside an admitted owner turn. It does not repair resumed sessions, changed installed SOUL contents, full compression rotation, or Responses input. Restricted prompts, final messaging delivery, complete source coverage, and ownership activation remain open. The endpoint scripts model responses; the host, plugin, SDK, hooks, connector, and native writes execute real code.

Exclusion uses exact normalized claims. It does not establish semantic paraphrase deletion or protection from hostile processes with the same operating-system identity. A current user quote remains distinct from ordinary recall. Forgotten text remains in transcripts and retained audit or backup material.
