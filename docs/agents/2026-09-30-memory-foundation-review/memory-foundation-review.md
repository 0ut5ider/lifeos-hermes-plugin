Date: 2026-09-30
Role: Independent implementation reviewer
Question: Does the committed memory foundation preserve native validation, record identity, governed writes, and truthful receipts, within its current scope?
Model: GPT-6 session model. The exact deployed model variant is not exposed to this reviewer.

# Memory foundation review

Reviewed commit: `bc0f06b31d57fc682176db59b37e3813d5c65f22` on `feature/lifeos-memory`.

The foundation has five confirmed defects. Three affect correction validation or forgotten facts. Two affect native record identity. The existing 14 tests pass against the actual native tools. Seven additional synthetic probes establish the findings and one recovery acceptance case. This review does not approve memory activation or claim that the provider, native hooks, MCP, privacy integration, or release are complete.

The primary agent received the confirmed validation, deletion, and forgotten-fact findings before this report. It started regression tests and fixes. The results below describe the reviewed commit. They do not evaluate those later fixes.

## Findings

### 1. High: hot correction bypasses the native private-content boundary

Location: `lifeos_hook_bridge/memory_access.py:280`, `lifeos_hook_bridge/memory_native.ts:31`.

`remember()` validates through `sanitizeTypedItemForPersistence`. Hot `correct()` sends its replacement directly to `MemoryWriter.setEntries`. That function validates entry structure but does not strip private spans.

The `private_hot_correction` probe corrects a synthetic rule to `RULE: public <private>SYNTHETIC_DENIED_MARKER</private>`. Calling the native sanitizer on this value returns `RULE: public `. The governed correction instead returns `committed`, and governed recall returns the private span in full.

Validate the normalized replacement through the same native capture boundary before any mutation. Reject content changes consistently with `remember()`, or define an explicit receipt for sanitization. Direct native curation must use this same validation when the managed adapter is implemented.

### 2. High: a rejected replacement can delete the original native fact

Location: `lifeos_hook_bridge/memory_access.py:283`, `lifeos_hook_bridge/memory_access.py:289`, `lifeos_hook_bridge/memory_access.py:292`.

The hot correction precheck only enforces a Python character count. Native `MemoryWriter.setEntries` can return `ok: true` while dropping a malformed or overlength entry. The original entry has already been removed from the submitted list. The native writer therefore publishes the removal, and `_record()` fails afterward because the replacement does not exist. SQLite rolls back its metadata changes, but the native file remains changed.

The `malformed_hot_correction` probe replaces one rule with text containing a newline. The native file then contains zero entries. The correction returns `unknown`. Recall raises `MemoryUnavailable` because the original row remains active. The same-key retry returns `unknown` again. The invalid replacement has therefore removed an acknowledged fact and made recall fail for that permitted record set.

Require complete entry validation before publication. Check the writer's actual accepted delta, including all dropped-entry counters. Cover JavaScript UTF-16 length rules, multiline entries, structural markers, and partial acceptance. Detecting the problem only after native publication is too late to prevent this data loss. This defect occurs without an interruption or a competing writer.

### 3. High: correction can reactivate a forgotten or superseded fact

Location: `lifeos_hook_bridge/memory_access.py:219`, `lifeos_hook_bridge/memory_access.py:260`.

`remember()` checks the digest against forgotten and superseded records. `correct()` does not perform this check on the replacement.

The `forgotten_correction` probe saves fact A, forgets A, and confirms that remembering A again is rejected. It then saves B and corrects B to A. The correction returns `committed`; ordinary recall returns A again. The request does not disclose or authorize reactivation of the forgotten record.

Apply one status and reactivation policy to every operation that introduces a fact, including corrections and managed native full-list writes. A correction request alone must not silently bypass the explicit reactivation decision required by the accepted design.

### 4. High: multiple active references can point to one deduplicated hot entry

Location: `lifeos_hook_bridge/memory_access.py:223`, `lifeos_hook_bridge/memory_access.py:292`, `lifeos_hook_bridge/memory_access.py:311`.

Native hot memory deduplicates equal entry strings. The metadata layer can independently create multiple active rows for that one native entry.

The `correction_merges_existing_hot_entry` probe saves distinct A and B, then corrects A to B. Native memory contains one B entry, but recall returns two B references. Forgetting either reference removes the native B entry while the other row remains active. Subsequent recall raises `MemoryUnavailable`.

The `duplicate_hot_project_metadata` probe reaches the same failure without correction. It remembers the same principal fact once with project `lab` and once with project `""`. The deduplication query treats these as distinct, although project does not distinguish native principal entries.

Canonicalize fields that do not apply to a native category. Establish one active identity per native hot entry, and define whether correction to an existing entry merges references or returns an existing reference. Forgetting a reference must update all identities that intentionally represent the same native entry. A same-content correction also needs an unchanged outcome instead of a new active row plus a superseded row with the same digest.

### 5. Medium: substring lookup accepts an ambiguous or stale section reference

Location: `lifeos_hook_bridge/memory_access.py:144`, `lifeos_hook_bridge/memory_access.py:147`, `lifeos_hook_bridge/memory_access.py:157`.

`_record()` locates the first occurrence of content anywhere in a file. `_content()` accepts the stored offset if its substring matches, or the first matching substring found elsewhere. Neither verifies a native entry or section boundary, nor refuses multiple matches.

The `ambiguous_reference_accepted` probe changes the original synthetic project section and adds two unrelated retained quotations of its original text. Correction using the original reference still returns `committed`. The unchanged metadata revision and a matching quotation suffice, even though the referenced section changed and the fallback match is ambiguous.

Use native entry or section identity and validate the associated revision. If references must temporarily use content matching, require an exact eligible section match and refuse ambiguity. Whole-file substring search cannot establish the accepted design's stale-edit and ambiguous-target guarantees. This is a reference defect; enforcing the managed-writer boundary remains separate scheduled work.

## Planned recovery work: measured acceptance evidence

The primary agent explicitly confirms that recovery transactions are scheduled next-phase work. This section records a concrete acceptance case, not a missing-foundation finding.

The `interrupted_native_publication` probe runs the real native writer in a child process. It exits with status 73 at the `_record` boundary, after native publication but before metadata insertion. A fresh `NativeMemory` instance then returns `unknown` for the original request ID and recalls no record. A new request ID appends the same synthetic fact a second time; the native note contains two copies.

The current durable reservation prevents automatic duplication under the same key and reports uncertainty honestly. Its digest and placeholder receipt are not sufficient to resolve publication after restart. The recovery implementation must reconcile the native publication with the operation and record metadata before accepting a replacement request. Retaining fact bodies only in native storage remains compatible with a durable publication protocol; the required operation and native-reference evidence must survive independently of the Python process.

## Native adapter invariants for the scheduled work

These points constrain the proposed extension. They are not additional implementation findings.

- Route every active native add and direct `MemoryWriter` curation path through the same serializer. Enforce the expected native revision inside the mutation transaction. A prior read outside that transaction does not protect a complete-list replacement.
- Preserve native validation, entry limits, drop counters, deletion guards, proposal decisions, and archive write results. A native `ok` flag alone does not prove that the requested content survived validation.
- Apply tombstone checks and identity handling to the resulting accepted native delta, including corrections and removals. Exact fingerprints only suppress exact normalized text; they do not establish semantic equivalence for paraphrases.
- Construct the native retrieval corpus from permitted current record sections. Passing a permitted path to whole-file retrieval can include superseded sections or sections with different project grants from the same note. Include native learning records only under an explicit status and audience policy.
- Make record, operation, revision, and policy metadata part of backup and restore consistency. Metadata is necessary for interpreting the authoritative native facts even when it contains no fact bodies.

The planned provider, MCP enrollment and revocation, prompt admission, model-request checks, native reviewer inputs, retention operations, UI, lifecycle, and release gates were not implemented or tested in this review. Their absence is not included in the defect count. In particular, the proposed required middleware extension has not been independently reviewed here.

## Evidence and limits

Baseline command: `python -m unittest discover -s tests -p 'test_memory*.py' -v`. Result: 14 tests passed in 2.476 seconds, with no skipped tests.

Probe command: `python docs/agents/2026-09-30-memory-foundation-review/raw/probe_foundation.py`. Result: all seven probes completed. The JSONL file records actual native outcomes, including the expected defect observations. These diagnostic probes are not passing regression assertions.

The fixtures use a fresh temporary home, native source symlinks, synthetic hot-memory scaffolds, and actual Bun/native operations. The interruption probe uses explicit process-failure injection. It does not mock the native backend. No real memories, production logs, `.211`, `.213`, memory services, or journal services were accessed. No server or agent configuration was changed. No implementation file was edited or committed by this reviewer.

Files:

- `raw/baseline-tests.txt`: exact baseline test output.
- `raw/probe_foundation.py`: full synthetic diagnostic script.
- `raw/probe-results.jsonl`: full final diagnostic output.
- `raw/commands.txt`: commands and evidence-preservation details.
- `raw/environment.txt`: commit and tool versions.
- `raw/source-hashes.json`: reviewed source hashes.
- `raw/committed-*`: committed foundation and design inputs.
- `raw/native-*`: inspected native source files, with no memory contents.

Review priority: resolve the private-content and destructive-validation defects first, then the reactivation and duplicate-identity defects. Verify stale section handling and the planned recovery transaction before activation. The native source copies establish the reviewed behavior; later edits to the shared checkout are outside this report's conclusions.
