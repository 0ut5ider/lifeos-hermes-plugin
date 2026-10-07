# 2026-10-05: Interrupted native import restores bytes but changes permissions

A real child process exits with status 73 after the principal native writer changes its file and before the operation commits. The journal restores the original bytes on the next transaction. Its file mode becomes decimal 384 (`0600`) instead of the original decimal 420 (`0644`). The new import target check correctly refuses that changed target.

The recovery journal stores file paths and original bytes, but no original mode. Its atomic publisher creates a private temporary file with mode `0600`. Recovery uses that publisher for every retained original file. The measured failure is a permission change during rollback, not duplicate import publication or a source mismatch.

The fix records original mode with each prepared file and restores that mode before publishing the replacement. Existing completed operations retain their current handling. The regression checks both bytes and mode, then resumes the same immutable import plan without duplicating the first committed item. Dynamic native publication also records original mode. Invalid mode metadata refuses recovery before any file changes. Historical journals without captured mode retain the existing private-mode restore behavior because their original mode is unknown.
