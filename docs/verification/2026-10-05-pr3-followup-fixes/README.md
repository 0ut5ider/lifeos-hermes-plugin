# Follow-up review corrections for pull request 3

Date: 2026-10-05. Two further independent reviews read the pull request. An [Opus reviewer](../../agents/2026-10-05-pr3-followup-review/pr3-followup-review.md) read the commits after the first review, `71987ce..c083037`. A [GPT-6 reviewer](../../agents/2026-10-05-pr3-memory-modules-review/pr3-memory-modules-review.md) read the memory modules that the first review did not read. Production on `.212` stays unchanged.

## Corrected in this unit

| Finding | Confirmation | Correction |
| --- | --- | --- |
| A planted bytecode file runs in place of the verified component source. | The new test plants an unchecked bytecode file beside the source. Before the correction, the planted program runs. | The loader reads the file once, checks the hash of those bytes, and runs those bytes. It no longer uses the source loader, so no bytecode file is read or written. |
| The loader opens the component twice and does not check the parent directory. | A component inside a world-writable parent loaded. | One read supplies both the hash and the program. The loader refuses a parent directory with shared write access. |
| An unreadable component breaks the memory status. | The status call raised a permission error. | The loader reports an unavailable component. |
| Revocation without the component leaves the SSH entry, and the page hides the action. | The page showed the action only for enabled connections. | The fallback marks the grant with `credential_entry_pending`. The page states that the entry remains and offers its removal when the component is available. A component revocation clears the mark. |
| Component removal follows a linked directory. | Removal deleted the program in the link target. | Removal refuses a directory that is not a physical owner directory. It also deletes the bytecode directory. |
| Fresh-store preparation fails when an unrelated setting changes. | The final check compared the complete configuration. | The check compares the root, the principal, and the account binding only. |
| An unreadable configuration on an unsupported host stops the plugin with an unclear error. | Registration raised the configuration error. | Registration raises `MemoryAdmissionError` with a clear statement. The plugin still does not load in that case, because it cannot confirm that lasting memory is disabled. |

The new tests fail before the correction ([before.txt](before.txt)). The final gate passes 102 tests ([after.txt](after.txt)), and the dashboard interface test passes 10 cases. The Hermes scan of the package stays `safe` with 46 findings, and the installer allows the package.

## Open findings from the memory module review

The primary agent confirms the first three by reading the code. None is reproduced by a test yet. Lasting memory is disabled on `.212`.

1. High. A client grant is checked only at the start of a call. A call in progress finishes after revocation (`memory_service.py`).
2. High. Recovery restores journal copies without a check for a later owner edit, unless the operation recorded an expected digest (`memory_transaction.py`).
3. High. Managed HTTP mode is held in process memory. After both marker files are lost and PULSE restarts, the direct routes serve without the managed checks (`lifeos-memory-access.patch`).
4. Medium. A repeated context migration replaces the earlier backup, because the backup name is fixed.
5. Medium. Proposal arguments have no size limit for nested values.

The GPT-6 reviewer read 36 memory modules completely and read the access patch by section.
