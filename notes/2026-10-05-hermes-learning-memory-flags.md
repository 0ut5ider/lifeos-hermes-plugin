# Disabled memory files remained editable through the learning graph

2026-10-05. The static import review identified a learning-graph gap. Real isolated Hermes processes confirm it: nine baseline failures show graph reads, details, edits, deletions, and independent per-store visibility ignoring disabled flags. A second baseline has four failures after an enabled store loads and the profile flags then change.

The graph needs current flags before source reads. Detail and mutation entry resolution needs the same check. Entry resolution runs again under the native memory file lock, so an already loaded store does not retain permission for the tested queued mutation. The final bridge gate passes 20 tests and 33 subtests. All 23 native graph tests also pass.

This is one boundary in the ownership transaction. Draining profile writers and coordinating configuration changes with file locks remain necessary. The patch preserves the original memory files. No running profile changes occur.
