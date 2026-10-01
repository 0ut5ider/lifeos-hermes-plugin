# Memory history repair second closure

Date: 2026-09-30

Role: Independent bounded closure reviewer

Question: Does the auxiliary proof correction restore clean generated requests while preserving retired-claim refusal and primary user-input protection?

Model: GPT-6. The exact model variant is not exposed in this agent context.

## Conclusion

**The original summary-helper regression is closed.** The unchanged archived proof-bearing child now succeeds for both primary and actual ContextCompressor requests, with clean stderr and one real HTTP request each.

The independent focused suite passed **68 tests in 127.266 seconds**, with no failures or skips. Source changes after the reviewed snapshot are recorded separately in raw/source-changes.json.

**One adjacent auxiliary-input omission remains confirmed:** a trusted auxiliary task other than compression can send an exact retired claim through the Responses API's string input. I reported the actual wire reproduction to the primary. This is denial coverage, distinct from automatic Responses history repair.

## Original finding, corrected

The runtime no longer applies the original human-input prefix proof to auxiliary requests. It disables primary history projection for those requests and checks generated user-role message content without the primary user exception.

I ran `docs/verification/2026-09-30-memory-history-repair/rerun_proof_compression.py` unchanged. That driver executes the archived `closure/raw/model_calls_with_proof.py` directly, so the changed source-replacement needle cannot invalidate the reproduction.

| Archived original operation | Process result | Output | HTTP requests |
| --- | --- | --- | ---: |
| Primary | 0; clean stderr | SYNTHETIC-MODEL-OK | 1 |
| Actual ContextCompressor summary | 0; clean stderr | A non-null summary containing SYNTHETIC-MODEL-OK | 1 |

The original archived child SHA-256 remains `c2b282f189216feac004ae21e41ebfa811b1a4f3575b4f9b7aa7973ca5ed6223`. It is copied into this evidence directory for preservation. Raw results and actual request bodies are in `raw/proof-compression.txt`.

The updated tests additionally exercise primary, synchronous auxiliary, asynchronous auxiliary, and actual compressor calls with an admitted original input proof. The runtime test confirms compression and memory_review cannot reuse the primary user exception for a retired claim in a user-role message.

## Remaining finding: non-compression auxiliary Responses strings evade inspection

Priority: medium, exact retired-claim admission omission.

Location: `memory_runtime.py`, `_messages` and the auxiliary-content checks in `_check_call`.

`_messages` deliberately skips a string-valued Responses `input`. The recursive inspection of the full input field is still conditional on `aux_task == 'compression'`. Other auxiliary tasks only scan message objects yielded by `_messages`, so their string input is never checked against retired claims.

### Actual SDK reproduction

`raw/probe_aux_responses.py` uses the real native fixture and official SDK with the approved local Responses route. It:

1. Saves and forgets a synthetic exact claim.
2. Admits a fresh session with the original-input proof.
3. Sends a primary Responses request as the explicit-user control.
4. Sends the same string input with trusted `aux_task='memory_review'`.

The child program is the existing model fixture with only its trusted auxiliary task changed from compression to memory_review. No native, policy, admission, SDK, or model-client method is replaced.

Both calls succeed and each sends one `/v1/responses` request. The auxiliary request body contains the exact forgotten marker, `Synthetic admitted private model marker`, in its string input. There is no warning or denial. The primary call is an intentional user-quote control; the auxiliary call must not inherit that exception under the new auxiliary policy.

Evidence:

- `raw/probe_aux_responses.py`: fixture driver.
- `raw/responses_memory_review.py`: exact child program.
- `raw/aux-responses.txt`: stdout, stderr, and actual HTTP bodies for both calls.

This was not a full AIAgent memory-review invocation. It directly exercises the same trusted task metadata and required middleware boundary with an actual supported SDK request. The omission concerns generated-input admission. Automatic projection or repair of Responses history remains outside scope.

Correction direction: apply complete generated-input inspection consistently to trusted auxiliary tasks, including string-valued Responses input. Retain the primary user-quote exception only for the appropriate primary input. Add paired accepted-current-content and rejected-retired-content cases using the real SDK.

## Independent focused results

| Module | Tests |
| --- | ---: |
| test_memory_agent | 6 |
| test_memory_history | 15 |
| test_memory_runtime | 25 |
| test_memory_model_calls | 11 |
| test_hermes_memory_provider | 7 |
| test_memory_host | 4 |
| Total | 68 |

The suite includes the previous concurrent-admission regression, original-input prefix handling, policy and identity refusals, and all six complete agent cases, including governed native LoadMemory correction and forget. All passed. The evidence runner records synthetic full-agent wire outcomes without replacing the test methods.

The focused run and original archived reproduction support closure of the reported summary-helper regression. They do not cover the newly identified string-input case until the separate probe is considered.

## Source and execution record

The exact production and test snapshots and SHA-256 hashes are in `raw/source-hashes.json` and adjacent files. Later source changes are recorded in `raw/source-changes.json` and are not claimed reviewed. Earlier initial and closure reports remain unchanged.

Exact commands are in `raw/commands.txt`. All runs use the complete memory-plugin-test-env Python, PYTHONPATH=.:tests, and explicitly selected owned app-startup Hermes and LifeOS sources. The endpoint is localhost; profiles and native records are synthetic.

I made no implementation edits or commits, used no live Hermes import or bootstrap, connected to no fleet machine, changed no account, and called no memory or journal tools.

## Remaining gates

Resume repair, changed installed SOUL repair, compression rotation, Responses repair, restricted prompts, and ownership activation remain open. This review closes the original helper availability regression and leaves the newly reproduced auxiliary denial omission for correction and verification. It makes no broader lifecycle or activation claim.
