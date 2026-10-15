# Retained native data after software removal

Date: 2026-10-15.

The joined removal publisher initially reuses the normal native memory transaction. That transaction requires `LIFEOS/TOOLS/MemorySystem.ts`. A complete removal deletes that tool. The independent review reproduces two failures: late apply recovery cannot resume, and software rollback stops all services before refusing the missing tool. The earlier synthetic publisher fixture retains the tool and misses both failures.

The removal publisher now uses a separate retained-data barrier. The barrier keeps the existing native data-root checks and shared writer lock. It opens the existing private SQLite registry, requires schema 4, takes `BEGIN IMMEDIATE`, and enables query-only mode. It does not create a schema, migrate a schema, recover a pending content journal, or write a fact. The normal native memory API still requires the installed tool. A pending native publication requires native recovery before removal.

The primary repeats all three independent probes, including the separate ancestor-directory guard failure. All three fail before correction. Ten focused controls and 39 combined controls pass after correction. The tests delete an actual private copy of `MemorySystem.ts`, resume interrupted publication, and restore software. They retain the original private data.

This result covers the publisher boundary. The complete preparer, owner dashboard action, standalone launch, and installed removal acceptance remain separate gates.
