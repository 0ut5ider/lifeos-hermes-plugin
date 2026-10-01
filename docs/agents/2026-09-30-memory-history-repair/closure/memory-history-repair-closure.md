# Memory history repair closure review

Date: 2026-09-30

Role: Independent bounded closure reviewer

Question: Do the concurrent-state and original-user-input fixes close the initial findings while preserving request admission and the existing model helper contract?

Model: GPT-6. The exact model variant is not exposed in this agent context.

## Conclusion

The two intended corrections pass independent verification: concurrent admission is preserved, and real native recall appended to the current user message is removed after correction or forgetting.

**Closure is incomplete because the new user-input proof introduces one confirmed availability regression.** The actual ContextCompressor summary helper rejects benign generated input whenever admission includes the original user-message proof. The primary request control with that same proof succeeds. The primary has been notified.

The focused suite passed 66 tests. Its model-helper tests omit user_message at admission and therefore do not expose this regression.

## Confirmed new finding: benign summary requests inherit the wrong input proof

Priority: medium, functional regression in an existing model helper.

Location: `memory_runtime.py`, final retained-message inspection in `_check_call`; `memory_history.py`, `retained_messages` and `user_parts`.

The original input proof describes the admitted human message. The runtime now applies that proof to the last user-role message in every request, including a trusted `aux_task=compression` request. ContextCompressor generates its own user-role summary instruction containing history and other material. That generated prompt cannot match the human input's prefix hash, so it is refused even when every piece of content is allowed and no fact was corrected or forgotten.

### Independent reproduction

`raw/probe_proof_compression.py` starts from the current real SDK/model helper. Its only behavioral change is to supply `user_message=settings['marker']` when admitting the synthetic session, matching the new host admission contract. The saved child source is `raw/model_calls_with_proof.py`.

| Operation with the same admitted input proof | Result | Actual HTTP requests |
| --- | --- | ---: |
| Primary request | SYNTHETIC-MODEL-OK | 1 |
| Actual ContextCompressor._generate_summary | null | 0 |

The compressor reports:

```text
Memory history cannot verify the current user input
Failed to generate context summary: Memory history cannot verify the current user input. Further summary attempts paused for 60 seconds.
```

The process exits successfully because the helper returns null on summary failure. Checking only process status would miss this failure. Full stdout, stderr, and wire observations are saved in `raw/proof-compression.txt`.

Correction direction: distinguish the primary human-input exception from trusted generated auxiliary input. Compression must still inspect all generated content for retired claims. It must not require that its generated prompt reproduce the original human-message prefix. A benign summary control with a real user proof and retired-content denial should both be tested.

This reproduction exercises the existing summary helper and its real SDK boundary. It does not claim to test a complete compression rotation or to implement history repair for compression.

## Initial finding 1: concurrent session state, verified corrected

I reran the original `probe_state_race.py` unchanged. It pauses the real repair after the first registry read, admits another session normally, then resumes repair.

The observed states now remain:

```text
repair snapshot:              [session]
after concurrent admission:   [concurrent-session, session]
after repair:                 [concurrent-session, session]
inactive retained check:      denied, ownership changed for retained context
```

The repair rereads the registry inside the cooperating native transaction before revalidation and publication. It preserves the concurrent session, and that retained lineage still prevents an inactive-config bypass.

The unchanged script exits 1 only because its final assertion requires the original defect to reproduce. The preceding raw output confirms the safe behavior. The new regression test uses the same real scheduling interleave and passes. Exact evidence: `raw/state-race.txt`.

## Initial finding 2: appended native recall, verified corrected

I executed the requested `capture_after.py` unchanged against the owned app-startup host and LifeOS sources. All six actual agent cases passed:

| Actual agent case | Model requests | Outcome |
| --- | ---: | --- |
| Remember | 2 | Native fact committed; authenticated receipt returned. |
| Unknown author | 0 | prompt_blocked before model access. |
| Correction after get | 3 | Committed correction receipt returned. |
| Forget after get | 3 | Committed forget receipt returned. |
| Real LoadMemory recall then correction | 3 | Retired recalled claim removed before final request. |
| Real LoadMemory recall then forget | 3 | Forgotten recalled claim removed before final request. |

The native-recall cases execute the actual configured native hook through the governed connector. Their first request includes the LifeOS recall wrapper and synthetic fact. Their third request excludes the retired claim. The original transcript is preserved, and native recall reflects the correction or forget result.

The admission state stores only input kind, length, and hash. For the exercised primary text and materialized block inputs, projection preserves the original prefix and examines the appended derived content. Tests also verify changed original input is refused and each new admitted turn binds its own input proof.

## Independent test results

**66 tests passed in 120.454 seconds**, no failures or skips:

| Module | Tests |
| --- | ---: |
| test_memory_agent | 6 |
| test_memory_history | 14 |
| test_memory_runtime | 25 |
| test_memory_model_calls | 10 |
| test_hermes_memory_provider | 7 |
| test_memory_host | 4 |

The six capture_after cases are additional executions of the same agent tests, not six distinct new tests. Their complete synthetic requests and outcomes are in `raw/capture-after.txt`. The unchanged race script and new proof/compressor probe are separate empirical checks.

The passing cases retain permission, route, author, destination, protocol-ID, transcript-preservation, extra_body, malformed-input, and system-instruction refusal coverage from the initial review. They do not establish universal support for every provider request representation.

## Source and artifacts

The initial closure snapshot of memory_history.py, memory_runtime.py, memory_provider.py and affected tests is saved in `raw/`, with exact SHA-256 hashes in `raw/source-hashes.json`. `raw/source-changes.json` records any later changes rather than silently treating them as the reviewed snapshot.

The commands, suite driver, unchanged race probe, unchanged capture script, and new compressor probe are retained under `raw/`. All runs use the complete memory-plugin-test-env Python and explicitly select the owned app-startup Hermes and LifeOS sources with PYTHONPATH=.:tests.

No implementation edits, commits, live imports/bootstrap, SSH, account changes, or memory/journal calls occurred. All profiles, native records, configuration writes, and HTTP endpoints were disposable synthetic fixtures.

## Open scope and next review

Resume repair, changed installed SOUL repair, compression rotation, Responses repair, restricted prompts, and ownership activation remain open. The summary-helper regression should be corrected and independently checked before this unit is considered closed. A passing fix for that helper will not by itself close the broader compression-rotation gate.
