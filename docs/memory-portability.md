# Memory import, return, and removal

Date: 2026-10-15. Status: implemented, qualified, and published in release 0.6.0. Development and daily select 0.6.0 through separate authenticated owner updates.

Adrian authorizes all six implementation stages and complete LifeOS software removal as an owner option. He also authorizes useful source content from `.213` and `.211`. Source stores remain intact. Personal source bytes and item reviews remain private and do not enter Git or public verification receipts. Shared `.211` records require the memory connector. A connector failure does not permit filesystem access to its records.

A fresh dashboard owner claim can lack the native memory connector. Ownership preparation binds a generated connector to the reviewed backup without publishing it. The separate ownership apply installs the connector under the writer barrier. Recovery restores its original absence only if its exact generated identity remains unchanged. Existing connector edits require another review.

The ownership review also identifies the local operating-system account, selected profile, model, and model-route hash. Application grants that local owner access to lasting memory through the reviewed route. It preserves unrelated grants and refuses conflicting local identities or restricted local destinations. Other accounts and unreviewed routes remain blocked. A model change requires a current review.

## Supported operations

1. Import reviewed built-in Hermes memory into a prepared or active LifeOS store.
2. Import a portable export from another store through an authenticated owner review.
3. Export current governed facts into a portable retained bundle and reviewed Hermes memory files.
4. Return the profile to built-in Hermes after verification of the selected memory files.
5. Remove the LifeOS software integration after return, with personal data and recovery copies retained.

## Use the dashboard controls

These operations require an authenticated installation owner. Installation and updates do not start them automatically.
Open **LifeOS Bridge** in the Hermes dashboard at `/lifeos-bridge` for import and export review.
Open **LifeOS releases** at `/lifeos-releases` for provider changes, recovery, and software removal.

To import memory:

1. Expand **Import Hermes memory**.
2. Select **Review Hermes memory** for this profile. For another profile, select its original files under **Import files from another Hermes profile**.
3. For a LifeOS export, use **Import a portable LifeOS bundle** and **Upload portable bundle for review**.
4. Review each entry. Select `import` or `exclude`, and check its category, text, title, and project.
5. Select **Review publication plan**.
6. Check the destinations and select **Apply reviewed import**.

Import preserves the source files and does not switch providers. If LifeOS ownership is disabled, the page offers **Prepare LifeOS ownership activation**.
That preparation requires a separate **Activate reviewed LifeOS ownership** approval on LifeOS releases.

To export memory:

1. Expand **Export memory and return to Hermes**.
2. Select **Review reverse export**.
3. Review current LifeOS facts and preserved Hermes entries. Select `export`, `retain`, or `exclude` for each item.
4. Select **Review export plan** and check the file text and character counts.
5. Select **Create reviewed export**.
6. Select **Download portable memory** to save the complete bundle.

Export does not switch providers or remove LifeOS. Retained items stay in the bundle and remain outside active Hermes recall.
Every item initially requires export before provider return. Clear **Required for provider return** only for an item that can remain outside active recall.

To return to built-in Hermes:

1. Complete a reviewed export whose plan reports **Ready for provider return: true**.
2. Enter the **Replacement Hermes prompt** that should replace the LifeOS prompt.
3. Select **Prepare return to built-in Hermes**.
4. Open **LifeOS releases** and inspect the prepared return workflow.
5. Select **Apply reviewed provider return** and verify its result.

There is no separate one-click restore of an old memory snapshot. To use only preserved Hermes memory, export the preserved Hermes entries.
Keep unwanted LifeOS facts retained in the bundle and clear their required status before reviewing the plan.
The return stops and disables Pulse, restarts Hermes, and keeps native data and exports. It leaves the integration software installed.

After a verified return, complete removal remains optional. On LifeOS releases, acknowledge Discord disablement and select **Prepare complete LifeOS removal**.
Review the software changes and save the displayed recovery command. Select **Remove reviewed LifeOS software** to apply the removal.
The integration page closes after successful removal. Use the saved command for authenticated recovery or software rollback.

The importer preserves each source occurrence and its original bytes. Each nonempty occurrence needs an import, hold, or exclude decision. The review shows the category, project, transformed content, exact duplicate, known retirement match, destination, and current readers. Existing `.253` facts win by default. Possible contradictions remain held until the owner resolves them. No automatic semantic merge or model classification runs.

The portable bundle preserves source references and origins. It distinguishes active Hermes entries from retained overflow and excluded material. Hermes character limits apply before publication. No automatic summary, truncation, or eviction makes content fit. Exported files use the supported Hermes delimiter and UTF-8 encoding.

Return and removal require a writer barrier, current source and destination checks, a private recovery journal, and fresh session verification. Interrupted operations resume or stop with an explicit conflict. Later edits remain intact. Return does not replay historical configuration over unrelated settings.

A newly reviewed activation after a verified return archives the matched terminal journals. A durable intent permits interrupted journal moves to resume. The archive retains the old plans and proofs. Activation does not replay their historical configuration or memory. The new ownership plan selects the current LifeOS plugins and installed native skills again.

Complete removal means that Hermes no longer loads the bridge, its hooks, prompts, memory provider, service overrides, or release manager. The operation stops LifeOS background services and removes only verified integration-owned software. Shared or changed program trees require a current verified replacement or a refusal. The operation retains source stores, exported knowledge, history, audit files, and recovery archives. Data erasure is a separate operation.

## Qualification stages

1. Establish source, destination, conflict, and removal contracts with characterization tests.
2. Complete authenticated import planning, application, status, and review controls for prepared and active stores.
3. Complete reverse export, capacity review, return, writer draining, and recovery.
4. Complete software removal with ownership checks and data retention.
5. Exercise real browser, service, session, failure, and retry paths in a disposable guest. Use synthetic fixtures and authorized source data.
6. Obtain an independent review, resolve measured findings, and qualify one complete release before daily deployment.

The current implementation state and reproducible test receipts live in `verification/2026-10-15-memory-portability/`. A passing primitive test does not establish a complete release gate.

## First supported complete removal

The removal action supports one managed default profile and its account native home. Preparation requires a verified provider-return operation and the same current native export. Later built-in Hermes memory remains intact. New native facts require a new export before removal. Preparation refuses changed software, another named profile, or another admitted consumer of the selected native programs or Bun command.

The owner explicitly acknowledges Discord disablement before preparation. Stock Hermes does not include the integration's private-channel restrictions. The operation retains the Discord credential and disables its platform configuration. It preserves unrelated model and provider settings.

The first standalone recovery command uses the existing password-authenticated dashboard owner. The helper verifies the retained code maps before it asks for authentication. It survives active manager removal and can resume removal or restore software. Software restoration keeps later built-in memory and does not restore historical LifeOS ownership. The owner must save the prepared command before application because the integration page disappears after successful removal.

The host must satisfy the stock Hermes tool prerequisites before removal preparation. Ubuntu 24.04 needs the `libatomic1` system package for the managed Node runtime. An administrator installs this prerequisite. An unprivileged background worker cannot complete an interactive `sudo` request. Preparation refuses before software removal if a required stock tool cannot start.

Release 0.6.0 is published. Installed checks verify normal removal, real stock model learning, reboot, authenticated software rollback, and exact 0.6 interrupted-removal recovery. The whole-guest restore, complete release qualification, and public latest installation replay pass. The [release record](verification/2026-10-15-release-0.6.0/README.md) identifies the exact checkpoints and preservation limits. The subsequent [deployment record](verification/2026-10-15-release-0.6.0-deployment/README.md) records separate owner updates on development and daily. Updating starts none of the memory portability workflows.

Removal preparation normalizes the retained environment with the pinned Hermes formatter before owner review. The review binds those exact bytes. Later environment edits still refuse publication and recovery. Invalid UTF-8 refuses before review.

Data-only profile backups declare `.lifeos-releases` and `.lifeos-portability` as runtime exclusions. Full guest backups retain those workspaces, standalone recovery helpers, and software rollback copies. The exact top-level exclusion preserves similarly named owner folders and nested workspace files.
