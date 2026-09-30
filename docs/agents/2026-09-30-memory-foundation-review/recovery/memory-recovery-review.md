Date: 2026-09-30
Role: Independent implementation reviewer, recovery verification
Question: Do the current foundation and rollback journal preserve native facts, references, and receipts across process crashes?
Model: GPT-6 session model. The exact deployed model variant is not exposed to this reviewer.

# Memory recovery review

All 22 memory tests pass. The previous 10 foundation probes also complete, including the Unicode and title-binding cases. Recovery works after a completed native write and after a committed receipt. Four concrete defects remain: a surviving native child can overwrite a later committed fact, the journal can snapshot a different path from the native writer, a crash before journal creation leaves a permanently unknown retry, and project references still accept changed bodies that retain the original prefix.

The reviewed working-tree files and their SHA-256 hashes are preserved under `raw/`. These conclusions apply to those snapshots, before the primary agent's subsequent fixes. This report does not assess provider, MCP, UI, release, or unbridged direct native writers.

## 1. High: the native child can publish after recovery releases its parent's lock

Locations: `memory_transaction.py`, `MemoryTransaction.lock`; `memory_access.py`, `NativeMemory._native`.

The Python process owns the flock descriptor. Its `subprocess.run` call does not pass that descriptor to Bun. Killing Python therefore releases the cooperating-writer lock while its native child can still execute. Recovery can restore the old file and allow another operation to commit before that child finishes.

The `native_child_outlives_parent_and_overwrites_later_commit` probe performs this sequence:

1. Save an original principal rule.
2. Start a governed correction and pause its real native `set_hot` operation before publication.
3. Kill the Python parent with SIGKILL.
4. Open a fresh access instance and recover the original rule.
5. Remember another principal rule and receive `committed`.
6. Resume the native child.

The native child exits successfully. Its old full-list replacement removes both the restored original and the later acknowledged fact. The native file contains only the orphan correction. Recall raises `MemoryConflict` because metadata still identifies the lost records as active.

The probe uses a temporary Bun gating script around the actual native worker. It does not mock the writer or its outcome. Delaying the write establishes a deterministic scheduling boundary for a native subprocess that remains alive after its parent. All files are synthetic.

Keep the recovery lock held for the complete lifetime of native publication, including surviving subprocesses. An inherited lock descriptor or another verified child-ownership protocol must prevent recovery and subsequent operations from overtaking a live native writer. This defect involves an in-flight governed operation. It does not depend on a direct writer that has not yet been bridged.

## 2. High: routing before sanitization journals the wrong file

Locations: `memory_access.py`, `_publication_paths`; `memory_native.ts`, `route` branch.

The journal routes the original item. The add path first sanitizes the item and routes the sanitized result. `_validate()` compares content but does not reject a changed title. Native capture sanitization can therefore change the target filename after the rollback snapshot has been selected.

The `sanitized_title_changes_journal_target` probe remembers a project fact with title `<private>hidden</private>Visible`. The journal records `private-hidden-private-visible.md`. The actual native writer creates `visible.md`. The child then exits with status 73 at `_record`, before metadata publication.

Restart recovery leaves `visible.md` intact because it restores the wrong target. Retrying the same request commits and appends the same fact again. The native note contains two occurrences.

Validate and canonicalize the complete native item before routing and preparing its publication. The journal and writer must use the same canonical target. Also verify that the actual returned native path belongs to the prepared target set before treating publication as complete.

## 3. Medium: a crash before journal preparation leaves a permanent unknown receipt

Location: `memory_access.py`, `_operation`, between reservation commit and `transaction.prepare`.

The first transaction commits an unknown operation receipt. The second transaction computes publication paths and writes the journal. A process exit between those stages leaves an unknown row and no journal. `recover()` has nothing to process, and retries return the same unknown receipt forever.

The `crash_before_journal_prepare` probe exits with status 73 at the start of `prepare()`. A fresh instance returns `unknown` for the same request ID, recalls no fact, and has no journal file. No native mutation occurred.

The durable operation state must distinguish an abandoned reservation from a published or publishing operation. Ensure that live operations cannot be mistaken for abandoned ones across the current lock-release gap. A same-key retry after restart should safely complete this never-started publication or return a durable known failure.

## 4. Medium: a project reference still identifies a prefix, not the complete fact section

Locations: `memory_access.py`, `_record` and `_content`.

Binding a project record to the final appended body fixes the previous title collision. `_content()` still reads only the originally saved number of characters and accepts their digest. If the actual body changes by extending that text, the stored slice remains identical.

The `changed_section_retains_original_text_as_prefix` probe changes the synthetic body from `The synthetic lab uses port 9123` to `The synthetic lab uses port 9123 is obsolete; use port 9443.`. Recall returns the truncated original claim. Correction through the original reference returns `committed` instead of a stale-reference conflict.

Validate the full identified native section and its revision. Use a section boundary that distinguishes an unrelated appended section from an extension of this fact. This is a remaining variant of the original reference-consistency finding. It does not claim that manual or unbridged native changes are already governed.

## Verified behavior

- The 22 memory tests pass in 9.843 seconds, with no skipped tests.
- The prior Unicode overlength correction now rejects before changing the original rule.
- The prior project title collision now produces a stale-reference conflict when the body changes.
- The previous private-span, newline, forgotten-fact, duplicate-reference, merge-state, and retained-quotation cases retain their corrected outcomes.
- An exit after native publication but before metadata insertion rolls back the target before retry. The existing crash test and repeated foundation probe confirm one final fact occurrence.
- An interrupted hot correction restores the original rule and reference. Retrying then commits the correction normally.
- An exit after the SQLite receipt commit but before journal cleanup preserves the committed fact. Restart returns the committed receipt and does not duplicate or undo the fact.
- The conflict receipt regression test passes, confirming the same receipt on retry for the tested stale-section conflict.

The rollback copies remain private transient recovery data. SQLite still stores metadata rather than fact bodies. The design of a temporary rollback copy is compatible with one authoritative fact store, provided recovery ordering is correct.

## Evidence and limits

The tests and probes use the existing disposable fixture with actual native source and Bun. No remote service, production memory, production log, Hermes runtime, bootstrap, or configuration was accessed. No implementation files were edited or committed by this reviewer.

The source review covers `memory_access.py`, `memory_transaction.py`, `memory_native.ts`, and the relevant native tests and source functions. Deterministic process-exit and scheduling probes exercise six recovery/reference cases. The earlier foundation script exercises ten cases. These probes record observed behavior; they are not a passing regression assertion suite.

This review establishes process-crash behavior at the tested boundaries. It does not establish host power-loss durability or filesystem failure behavior. The publication paths include file and SQLite durability concerns that need a separate power-loss model before making that guarantee.

Artifacts:

- `raw/tests-22.txt`: complete 22-test output.
- `raw/foundation-probes.jsonl`: rerun of all ten prior foundation probes.
- `raw/probe_recovery.py`: full recovery and reference probe script.
- `raw/recovery-probes.jsonl`: all six final diagnostic results.
- `raw/reviewed-*`: source snapshots for the reviewed working tree.
- `raw/reviewed-hashes.json`: snapshot hashes.
- `raw/commands.txt`: exact execution commands.

The primary agent received each confirmed recovery defect promptly. Priority should go to the surviving native child, because it can delete an unrelated acknowledged write. Resolve canonical routing and abandoned reservation recovery next. Complete section identity still needs verification before claiming stale-edit protection for project records.
