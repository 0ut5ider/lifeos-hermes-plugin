Date: 2026-09-30
Role: Independent reviewer, bounded foundation review closure
Question: Does the native section delimiter fix close the remaining finding, and does governed native BM25 preserve authorized current-record retrieval?
Model: GPT-6 session model. The exact deployed model variant is not exposed to this reviewer.

# Foundation review closure

The bounded foundation review is closed with no remaining confirmed finding in the reviewed functions. All 28 memory tests pass. The exact heading reproduction now saves and recalls intact. Independent probes confirm that native BM25 receives only authorized current records and that supplied-corpus searches do not reuse another corpus's cache entries.

This conclusion applies to the working-tree snapshots and managed native source recorded in `raw/reviewed-hashes.json`. It does not approve ownership activation, remote sharing, or the integrations that are still planned.

## Remaining heading finding is fixed

The exact reproduced content is:

```text
Synthetic first paragraph
## Appended experiment notes
Synthetic second paragraph
```

The save returns `committed`. Immediate recall returns the entire original content and the same reference. The native section boundary now requires both the native timestamp heading and its source comment. Native write validation rejects comment markup in user content, so the ordinary user heading no longer acts as a native boundary.

The existing tests also retain coverage for a stale body that preserves its old prefix, stale quotations elsewhere in a note, and title/body text collisions. Those tests pass.

## Native retrieval verification

The reviewed access code selects active rows, applies category and project grants, reads their verified current content, and constructs the supplied native corpus. It uses opaque record IDs as retrieval paths. The result assembly resolves returned IDs against that authorized record map and returns authoritative fact content with the native score.

The native helper requires `SUPPLIED_CORPUS_API_VERSION == 1`. It calls the existing native BM25 function with the supplied corpus. The managed-source patch selects that corpus instead of filesystem discovery and skips both cache reads and writes for supplied-corpus calls.

The independent `authorized_current_corpus` probe saves synthetic records that include:

- An allowed project fact containing the formerly failing heading.
- A denied principal fact.
- A denied fact for another project, stored in the same native note as allowed facts.
- A superseded project fact and its permitted current correction.

Recall under the project reader grant returns exactly the allowed heading fact and current correction. The output contains no denied principal marker, other-project marker, or superseded marker. The result set preserves the correction reference.

The independent same-process probe warms the ordinary native cache and then uses the same query with supplied corpus A, corpus B, and an empty corpus:

| Call | Result paths | Cached |
| --- | --- | --- |
| First supplied corpus | `FIRST_ALLOWED` only | false |
| Second supplied corpus | `SECOND_ALLOWED` only | false |
| Empty supplied corpus | none; total searched is 0 | false |
| Ordinary retrieval after supplied calls | The original ordinary result set | true |

This verifies that scoped queries neither consume nor replace the ordinary cache. The empty supplied corpus does not fall back to filesystem discovery. The ordinary native call in this probe uses the disposable synthetic fixture only; it is not an integration claim about governing unbridged native retrieval.

## Test results

Command: `python -m unittest discover -s tests -p 'test_memory*.py' -v`.

Result: 28 tests passed in 13.495 seconds, with no skipped tests. The suite includes the previously verified recovery ordering, surviving native child lock, correction validation, identity, receipt retry, and stale-reference cases.

Command: `python docs/agents/2026-09-30-memory-foundation-review/closure/raw/probe_closure.py`.

Result: all three independent probes completed and their assertions passed. Full outputs are in `raw/probe-results.jsonl`.

## Scope and limits

The inspected changes are the project section boundary in `memory_access.py`, the authorized-corpus construction and native result mapping, the `rank` branch in `memory_native.ts`, and the supplied-corpus patch to the managed native `MemoryRetriever.ts`. The test fixture now uses `/home/outsider/.cache/lifeos-plugin-memory/managed-source/LifeOS/install`.

All operations used temporary synthetic fixtures and actual native tools. No production memories or logs, remote runtime, deployed configuration, memory service, or journal service were accessed. This reviewer made no implementation changes or commits.

Native delegation, provider integration, MCP, UI, model-input privacy enforcement, installation lifecycle, and activation remain outside this closure. Host power-loss behavior and large-corpus performance were not established. The review found no new meaningful defect in the bounded edited functions; it is not a claim that the entire memory feature is complete.

Artifacts:

- `raw/tests-28.txt`: complete test output.
- `raw/probe_closure.py`: exact synthetic heading, corpus, and cache probes.
- `raw/probe-results.jsonl`: complete independent probe output.
- `raw/reviewed-*`: reviewed access code, native helper, patch, tests, and managed native retriever.
- `raw/reviewed-hashes.json`: SHA-256 hashes.
- `raw/commands.txt`: exact test and inspection commands.
