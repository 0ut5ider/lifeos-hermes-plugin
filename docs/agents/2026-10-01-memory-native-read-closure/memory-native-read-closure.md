Date: 2026-10-01
Agent role: Independent closure reviewer
Question: Do the current retained-source validation and traversal corrections close the two P2 findings without a material regression in neighboring read behavior?
Model: Assigned gpt-6-astra with high effort. The runtime model identifier is not independently exposed to this agent.

Adrian, both P2 findings are closed in the reviewed working diff. The source validator now receives the complete retained source path as well as its body. Directory iteration now stops on entry 2,049, before filtering or sorting, under one counter shared by all retained roots. I found no additional material defect in these corrections or the adjacent paths examined.

This is a scoped read-path closure. It does not clear publication, lifecycle, or ownership release. Ownership should remain disabled under the existing release plan.

The reviewed repository is `/home/outsider/Projects/Hermes_agent/LifeOS_plugin`, branch `feature/lifeos-memory`, based on `d920dd1` with the three uncommitted correction files. `raw/reviewed.diff`, `raw/source-manifest.json`, and `raw/sources/` preserve the reviewed implementation and tests. The review used synthetic temporary fixtures and local native Bun processes. It did not connect to a real deployment, call memory or journal tools, change product code or prepared source snapshots, commit, or push.

Closure finding 1: P2 private and control text in source labels, closed.

The correction is at `lifeos_hook_bridge/memory_sources.py:101`. Each native validation input contains the original body, a newline, and the full original path. A failed validation excludes that entire source before `memory_wiki.py:95` combines it with its slug and group. The history check still covers the body, relative path, and normalized labels at `memory_sources.py:107`.

The native validator at `lifeos_hook_bridge/memory_native.ts:104` applies the established private-boundary and canonical control-character checks. All variable retained-source labels come from either the checked body or checked path. The category and added slug prefixes come from fixed collector constants. The timestamp is formatted from the filesystem timestamp. The fixed system-prompt filename does not bypass body validation. No unchecked external metadata input is introduced by this correction.

The isolated metadata probe covers six path cases:

| Source location | Rejected text |
| --- | --- |
| DOCUMENTATION filename | Literal private opener |
| DOCUMENTATION parent group | Private opener with an inserted zero-width character |
| WORK directory | Private opener using full-width letters |
| WISDOM filename | U+0085 control |
| RESEARCH filename | U+007F control |
| ALGORITHM filename | Malformed private opener |

Each source has an ordinary body and a link to an admitted target. A separate fixed `LIFEOS_SYSTEM_PROMPT.md` contains private body text. The native index, graph, search, document, and backlink responses contain none of the rejected markers. All excluded raw files retain their original contents. An ordinary filename without a title still supplies the native fallback title, and its `Public Group` parent remains the native group.

Backlinks received a separate check. In the prepared native `LIFEOS/PULSE/modules/wiki.ts:497`, `rebuildBacklinks` derives entries from the admitted page index. `handleBacklinks` at line 1001 returns those entries without requiring the target page to exist. The probe confirms the admitted ordinary source supplies exactly one backlink to both an existing target and an unpublished target. Excluded source labels never supply backlinks. A target with no incoming link returns an empty list. This preserves native backlink behavior and does not claim that unknown-target links constitute source publication or target authorization.

Closure finding 2: P2 unbounded discovery before refusal, closed.

`lifeos_hook_bridge/memory_wiki.py:20` uses the real streaming `os.scandir` iterator. The counter check runs before the next entry is appended to the bounded list. Sorting therefore only sees a bounded list. `_retained_sources` creates one counter at line 56 and passes it through DOCUMENTATION, ALGORITHM, WORK, LEARNING, WISDOM, and RESEARCH. WORK uses the same helper at line 77. Hidden and non-source entries consume the budget before selection. The separate selected-source count remains at line 60.

The observer wraps the real iterator and counts yields. It does not synthesize directory entries or replace the filesystem reader. Each case has an isolated fixture, so a private-label exclusion cannot mask a traversal result.

| Fixture population | Actual yielded entries | Observed result |
| --- | ---: | --- |
| 6,000 visible non-Markdown entries | 2,049 | Traversal refusal |
| 3,000 hidden entries | 2,049 | Traversal refusal |
| Exactly 2,048 hidden entries | 2,048 | Successful empty selection |
| 2,049 hidden entries | 2,049 | Traversal refusal |
| 3,000 non-source WORK entries | 2,049 | Traversal refusal |
| 1,100 entries in each of DOCUMENTATION, ALGORITHM, and WORK | 2,049 total | 1,100 DOCUMENTATION plus 949 ALGORITHM entries, then refusal; WORK is not visited |

The refusal necessarily consumes entry 2,049 to detect excess population. It does not append that entry, materialize the remaining population, or sort the oversized directory. This is a bound on application directory discovery, not a measured whole-request latency guarantee or a claim about operating-system directory buffering.

Verification evidence:

1. The detached `run_closure.py` job reran `test_memory_wiki_corpus`, `test_memory_wiki_render`, `test_memory_sources`, and `test_memory_canonical`. All 66 tests pass in 47.903 seconds, with no skips, failures, or errors. Exact command and output are in `raw/focused-tests.txt`; `raw/focused-tests.done` contains `0`.
2. The first seven independent probe cases passed under that runner. Three explicit path-guard cases were then added to the probe and the probe alone was rerun. The final ten cases pass. `raw/probes-final.txt` records the final completion, and `raw/closure-probes.json` preserves counts, refusal messages, and complete native responses. The initial runner markers refer to the initial seven-case probe and the unchanged 66-test run.
3. The explicit path probes confirm that a WORK `ISA.md` symlink, a nested DOCUMENTATION directory symlink, and a lexical parent traversal all refuse. The existing rerun tests also cover redirected roots and sources, duplicate slugs, private bodies, current policy and retirement checks, invalid UTF-8, source size limits, native standalone comparisons, and later empty-corpus isolation.
4. The source hashes were checked after verification. `raw/final-checks.json` records whether each reviewed implementation and test file still matches the captured snapshot. The same file records `git diff --check` output and status.

To reproduce the final probes from the repository root, use the test-environment Python with `PYTHONPATH=.:tests`, `LIFEOS_MEMORY_SOURCE=/home/outsider/.cache/lifeos-plugin-memory/source-gate-20261001-knowledge-relay-final/lifeos/LifeOS/install`, and `LIFEOS_HERMES_SOURCE=/home/outsider/.cache/lifeos-plugin-memory/source-gate-20261001-knowledge-relay-final/hermes`. Run `docs/agents/2026-10-01-memory-native-read-closure/probe_closure.py`. Its source contains every fixture and assertion. `run_closure.py` records and runs the complete focused command with the same environment.

Known limits remain distinct from defects in these corrections. Private-boundary examples still exclude entire documentation files. Conservative retirement still excludes older unclassified documentation. Managed whole-note writes, publication provenance, actual mount and sidecar publication, inventory completeness, lifecycle coverage, and recoverable ownership setup remain outside this closure. The review did not rerun all 514 memory tests or independently repeat the primary agent's 124-test combined gate. Its independent 66-test result and ten probe cases establish the narrower claim above.

The review decision worth retaining is that the 2,048-entry traversal budget includes hidden files and non-source entries across all selected roots. A sufficiently populated retained tree now refuses the complete wiki view. That behavior is intentional under the requested bound. These tests do not establish an atomic snapshot against arbitrary external filesystem writers, a maximum time under lock contention, or readiness to enable ownership. The reviewer made no external-system change to undo.
