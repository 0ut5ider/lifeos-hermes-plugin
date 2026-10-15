# Memory import, return, and removal

Date: 2026-10-15. Status: implementation and qualification in progress.

Adrian authorizes all six implementation stages and complete LifeOS software removal as an owner option. He also authorizes useful source content from `.213` and `.211`. Source stores remain intact. Personal source bytes and item reviews remain private and do not enter Git or public verification receipts. Shared `.211` records require the memory connector. A connector failure does not permit filesystem access to its records.

## Supported operations

1. Import reviewed built-in Hermes memory into a prepared or active LifeOS store.
2. Import a portable export from another store through an authenticated owner review.
3. Export current governed facts into a portable retained bundle and reviewed Hermes memory files.
4. Return the profile to built-in Hermes after verification of the selected memory files.
5. Remove the LifeOS software integration after return, with personal data and recovery copies retained.

The importer preserves each source occurrence and its original bytes. Each nonempty occurrence needs an import, hold, or exclude decision. The review shows the category, project, transformed content, exact duplicate, known retirement match, destination, and current readers. Existing `.253` facts win by default. Possible contradictions remain held until the owner resolves them. No automatic semantic merge or model classification runs.

The portable bundle preserves source references and origins. It distinguishes active Hermes entries from retained overflow and excluded material. Hermes character limits apply before publication. No automatic summary, truncation, or eviction makes content fit. Exported files use the supported Hermes delimiter and UTF-8 encoding.

Return and removal require a writer barrier, current source and destination checks, a private recovery journal, and fresh session verification. Interrupted operations resume or stop with an explicit conflict. Later edits remain intact. Return does not replay historical configuration over unrelated settings.

Complete removal means that Hermes no longer loads the bridge, its hooks, prompts, memory provider, service overrides, or release manager. The operation stops LifeOS background services and removes only verified integration-owned software. Shared or changed program trees require a current verified replacement or a refusal. The operation retains source stores, exported knowledge, history, audit files, and recovery archives. Data erasure is a separate operation.

## Qualification stages

1. Establish source, destination, conflict, and removal contracts with characterization tests.
2. Complete authenticated import planning, application, status, and review controls for prepared and active stores.
3. Complete reverse export, capacity review, return, writer draining, and recovery.
4. Complete software removal with ownership checks and data retention.
5. Exercise real browser, service, session, failure, and retry paths in a disposable guest. Use synthetic fixtures and authorized source data.
6. Obtain an independent review, resolve measured findings, and qualify one complete release before daily deployment.

The current implementation state and reproducible test receipts live in `verification/2026-10-15-memory-portability/`. A passing primitive test does not establish a complete release gate.
