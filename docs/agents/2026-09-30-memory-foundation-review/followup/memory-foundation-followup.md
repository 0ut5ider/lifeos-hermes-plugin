Date: 2026-09-30
Role: Independent implementation reviewer, foundation fix verification
Question: Do the working-tree fixes resolve all five foundation findings, and do the edited correction paths preserve native content and exact metadata state?
Model: GPT-6 session model. The exact deployed model variant is not exposed to this reviewer.

# Memory foundation follow-up

The 19 tests pass. The original private-span, newline, reactivation, duplicate-reference, and retained-quotation cases now behave as intended. Two findings remain incomplete: native overlength validation still permits destructive correction for supplementary Unicode characters, and project references can still bind to title text instead of the fact body.

This review covers the working-tree versions preserved in `raw/reviewed-memory_access.py` and `raw/reviewed-test_memory_native.py`. Their hashes appear in `raw/reviewed-hashes.json`. The primary agent may have changed the shared checkout after these snapshots. This report does not assess those later changes.

## Findings that remain

### 1. High: supplementary Unicode bypasses the hot-entry length check

Location: `lifeos_hook_bridge/memory_access.py:164` and the correction `set_hot` call.

The new shared `_validate()` checks Python `len()` of the body. Native `MemoryWriter` checks JavaScript string length, which counts UTF-16 code units. Each U+1F600 character therefore counts as one in Python and two in the native writer.

The `unicode_overlength_hot_correction` probe starts with one acknowledged rule. It submits `RULE: ` followed by 129 U+1F600 characters as the correction. Python counts 129 body characters; the native writer counts 258 and drops the entry. The native file becomes empty. The correction returns `unknown`, and recall raises `MemoryConflict` because the original metadata remains active.

This is the same destructive partial-acceptance defect reported originally, through a different accepted input. It does not require an interrupted write. Match native length validation before mutation and verify that the intended accepted delta cannot discard the replacement. A rejected correction must leave both the native fact and its active reference unchanged.

### 2. Medium: initial substring binding still permits a stale project correction

Location: `lifeos_hook_bridge/memory_access.py:148` and `lifeos_hook_bridge/memory_access.py:178`.

Removing the project fallback search fixes the original retained-quotation case. However, `_record()` still uses `text.find(content)` across the whole note. If the title contains the fact text, the stored position identifies the YAML title or heading. `_content()` accepts that stored substring without checking that it is the fact body.

The `project_reference_binds_title_instead_of_body` probe remembers a project fact with the same title and content: `Synthetic exact title marker`. It then changes only the actual body to `Synthetic changed body marker`. Ordinary recall still returns the original title text as the fact. Correction through the original reference returns `committed` instead of a stale-reference conflict.

Bind the reference to the native fact section at creation and verify that same complete section on access. A valid stored offset must identify eligible fact content. The absence of a fallback scan does not establish this invariant.

## Verified fixes and exact correction state

| Original concern | Follow-up evidence | Result |
| --- | --- | --- |
| Private content in a hot correction | Native sanitizer changes the input; correction returns rejected; private marker is absent from recall | Fixed for the reproduced case |
| Newline replacement deletes original | Correction returns rejected; original native rule and reference remain; retry returns the same rejection | Fixed for newline, but Unicode variant above remains |
| Correction reactivates forgotten text | Correction returns rejected; forgotten text stays absent | Fixed for the reproduced case |
| Different project fields alias a hot entry | Second remember returns unchanged with the first reference; forgetting leaves empty recall | Fixed for the reproduced case |
| Correcting A to existing B creates aliases | Correction returns B's existing reference; recall returns one B; forgetting B leaves empty recall | Fixed for the reproduced case |
| Changed original section resolves through quotations | Correction returns conflict and does not append replacement | Fixed for fallback quotations, but initial title binding above remains |

The additional `exact_unchanged_merge_state` probe checks database metadata alongside the real native file:

- Correcting A to the same normalized content returns `unchanged` with A's original reference and revision.
- Correcting A to existing B returns `committed` with B's reference.
- The database contains B as active at revision 1 and A as superseded at revision 2. Both have the canonical empty project value for principal memory.
- Native hot memory contains one B entry.
- Correcting A again using its original reference returns `conflict`.

These observations confirm the intended state transitions for the edited same-content and merge branches. They do not establish behavior for all native curation paths scheduled for later implementation.

## Tests and diagnostic execution

Command: `python -m unittest discover -s tests -p 'test_memory*.py' -v`.

Result: 19 tests passed in 4.182 seconds. No tests were skipped. Full output is in `raw/tests-19.txt`.

The original diagnostic script was rerun unchanged. Its first five cases completed with corrected outcomes. It then exited with status 1 because the retained-quotation case calls recall after deliberately corrupting the recorded body, and the stricter lookup now raises `MemoryConflict`. That complete traceback is preserved in `raw/original-probes.stderr`. The failure does not indicate that the stale correction was accepted.

A follow-up copy catches that expected recall exception so all original cases can complete. It also adds the Unicode, title-binding, and exact-state probes. All 10 diagnostic cases completed, and their real native outcomes appear in `raw/probe-results.jsonl`. The script records observations; it is not a passing regression suite.

## Explicitly deferred recovery work

The interruption probe still shows the scheduled recovery behavior: an exit after native publication leaves the original request `unknown`; a new request ID appends another copy. This was already assigned to recovery transactions and is not counted as a new finding.

The primary agent also explicitly defers persistence of `MemoryConflict` receipts raised outside the callback result path. `_operation()` currently returns that conflict while the durable reserved receipt remains unknown. This follow-up does not treat that known recovery-phase item as an unresolved fix in the current batch.

## Scope and artifacts

Only disposable synthetic native fixtures were used. The review did not read production memories or logs, contact remote systems, run a Hermes runtime or bootstrap, change configuration, or edit implementation code. New files are review artifacts only.

Artifacts:

- `raw/tests-19.txt`: complete test output.
- `raw/original-probes.jsonl` and `raw/original-probes.stderr`: unchanged diagnostic rerun output and traceback.
- `raw/probe_followup.py`: follow-up diagnostic script.
- `raw/probe-results.jsonl`: all 10 diagnostic outputs.
- `raw/reviewed-memory_access.py` and `raw/reviewed-test_memory_native.py`: reviewed working-tree sources.
- `raw/reviewed-hashes.json`: source hashes.
- `raw/commands.txt`: exact execution commands and interpretation.

The two remaining issues should receive failing regression tests before another verification pass. The Unicode case must preserve the original native rule after rejection. The title case must identify a stale body even when identical text remains in metadata or headings.
