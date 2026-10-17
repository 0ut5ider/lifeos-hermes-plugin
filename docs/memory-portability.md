# Memory import, return, and removal

Status: supported in the complete integration. The [current release record](verification/2026-10-16-release-0.7.3/README.md) identifies qualification and deployment. The original portability acceptance remains in the [0.6.0 record](verification/2026-10-15-release-0.6.0/README.md).

Import, export, provider return, and software removal are separate authenticated owner actions. Installation and updates do not run them automatically. Source stores remain intact. Keep source bytes, reviewed items, and private exports outside Git. Remote source access requires its authorized connector; a connector failure does not permit filesystem access to memory records.

A fresh dashboard owner claim can lack the native memory connector. Ownership preparation binds a generated connector to the reviewed backup without publishing it. The separate ownership apply installs the connector under the writer barrier. Recovery restores its original absence only if its exact generated identity remains unchanged. Existing connector edits require another review.

The ownership review also identifies the local operating-system account, selected profile, model, and model-route hash. Application grants that local owner access to lasting memory through the reviewed route. It preserves unrelated grants and refuses conflicting local identities or restricted local destinations. Other accounts and unreviewed routes remain blocked. A model change requires a current review.

## Use the dashboard controls

These workflows need the authenticated installation owner and current source review. Import, export, provider return, and removal do not run automatically during installation or updates.

| Task | Start in the dashboard | Result |
| --- | --- | --- |
| Import current Hermes memory | **LifeOS Bridge** > **Lasting memory** > **Import Hermes memory** > **Review Hermes memory** | Review source entries and publication decisions before applying the import |
| Import another profile or portable bundle | The same import section, then **Import files from another Hermes profile** or **Import a portable LifeOS bundle** | Private source upload and owner review; source files stay intact |
| Create reverse export | **Export memory and return to Hermes** > **Review reverse export** | Select active Hermes entries, retained overflow, and exclusions |
| Switch back to Hermes | Prepare return from the completed export, then review it in **LifeOS releases** | A separate owner-authorized provider change |
| Remove LifeOS software | The verified return in **Advanced: memory ownership and removal** | A separate reviewed software-removal operation that retains data |

Ownership activation after import requires **Review publication plan**, **Apply reviewed import**, a published result with required entries verified, then **Prepare LifeOS ownership activation**. The Releases page reviews and applies that separate workflow. An entirely empty review currently lacks the publication-plan button; see the [activation limit](installation-workflow.md#choose-memory-ownership-separately).

For reverse export and return:

1. Select **Review reverse export** in the Bridge page.
2. Decide which current facts and preserved Hermes occurrences to export, retain, or exclude. Resolve every item required for return.
3. Select **Review export plan** and check the resulting `MEMORY.md`, `USER.md`, character limits, and return readiness.
4. Select **Create reviewed export**. Use **Download portable memory** to retain the bundle privately.
5. Enter the replacement Hermes prompt and select **Prepare return to built-in Hermes** when the export is ready.
6. Open **LifeOS releases**, then **Advanced: memory ownership and removal**.
7. Review the prepared return and select **Apply reviewed provider return**.
8. Verify the resulting provider and fresh Hermes session before proceeding with removal.

To use preserved Hermes entries, select those occurrences in the export review. Review any newer LifeOS facts separately. The return uses the reviewed current files; it does not silently restore an old profile backup.

For complete software removal:

1. Start from a verified provider-return workflow in **LifeOS releases**.
2. Acknowledge that removal disables Discord because stock Hermes lacks the integration's private-channel restrictions.
3. Select **Prepare complete LifeOS removal**.
4. Save the displayed standalone recovery command before applying. The manager page disappears after removal.
5. Review the exact software changes and select **Remove reviewed LifeOS software**.

Use **Recover memory workflow**, **Restore previous provider settings**, or **Restore integration software** only when offered for the operation's actual state. If the page is unavailable, use the retained standalone recovery path and its owner authentication. Preserve the journal and later edits.

## Supported operations

1. Import reviewed built-in Hermes memory into a prepared or active LifeOS store.
2. Import a portable export from another store through an authenticated owner review.
3. Export current governed facts into a portable retained bundle and reviewed Hermes memory files.
4. Return the profile to built-in Hermes after verification of the selected memory files.
5. Remove the LifeOS software integration after return, with personal data and recovery copies retained.

The importer preserves each source occurrence and its original bytes. Each nonempty occurrence needs an import, hold, or exclude decision. The review shows the category, project, transformed content, exact duplicate, known retirement match, destination, and current readers. Existing destination facts win by default. Possible contradictions remain held until the owner resolves them. No automatic semantic merge or model classification runs.

The portable bundle preserves source references and origins. It distinguishes active Hermes entries from retained overflow and excluded material. Hermes character limits apply before publication. No automatic summary, truncation, or eviction makes content fit. Exported files use the supported Hermes delimiter and UTF-8 encoding.

Return and removal require a writer barrier, current source and destination checks, a private recovery journal, and fresh session verification. Interrupted operations resume or stop with an explicit conflict. Later edits remain intact. Return does not replay historical configuration over unrelated settings.

A newly reviewed activation after a verified return archives the matched terminal journals. A durable intent permits interrupted journal moves to resume. The archive retains the old plans and proofs. Activation does not replay their historical configuration or memory. The new ownership plan selects the current LifeOS plugins and installed native skills again.

Complete removal means that Hermes no longer loads the bridge, its hooks, prompts, memory provider, service overrides, or release manager. The operation stops LifeOS background services and removes only verified integration-owned software. Shared or changed program trees require a current verified replacement or a refusal. The operation retains source stores, exported knowledge, history, audit files, and recovery archives. Data erasure is a separate operation.

## Qualification evidence

The [portability verification record](verification/2026-10-15-memory-portability/README.md) records the component, browser, service, session, interruption, and recovery gates. The [0.6.0 release](verification/2026-10-15-release-0.6.0/README.md) qualifies the complete workflow. The current release record above identifies later deployment. A passing primitive test does not establish a complete release gate.

## First supported complete removal

The removal action supports one managed default profile and its account native home. Preparation requires a verified provider-return operation and the same current native export. Later built-in Hermes memory remains intact. New native facts require a new export before removal. Preparation refuses changed software, another named profile, or another admitted consumer of the selected native programs or Bun command.

The owner explicitly acknowledges Discord disablement before preparation. Stock Hermes does not include the integration's private-channel restrictions. The operation retains the Discord credential and disables its platform configuration. It preserves unrelated model and provider settings.

The first standalone recovery command uses the existing password-authenticated dashboard owner. The helper verifies the retained code maps before it asks for authentication. It survives active manager removal and can resume removal or restore software. Software restoration keeps later built-in memory and does not restore historical LifeOS ownership. The owner must save the prepared command before application because the integration page disappears after successful removal.

The host must satisfy the stock Hermes tool prerequisites before removal preparation. Ubuntu 24.04 needs the `libatomic1` system package for the managed Node runtime. An administrator installs this prerequisite. An unprivileged background worker cannot complete an interactive `sudo` request. Preparation refuses before software removal if a required stock tool cannot start.

Release 0.6.0 is published. Installed checks verify normal removal, real stock model learning, reboot, authenticated software rollback, and exact 0.6 interrupted-removal recovery. The whole-guest restore, complete release qualification, and public latest installation replay pass. The [release record](verification/2026-10-15-release-0.6.0/README.md) identifies the exact checkpoints and preservation limits. The historical 0.6.0 acceptance does not select a later installed release.

Removal preparation normalizes the retained environment with the pinned Hermes formatter before owner review. The review binds those exact bytes. Later environment edits still refuse publication and recovery. Invalid UTF-8 refuses before review.

Data-only profile backups declare `.lifeos-releases` and `.lifeos-portability` as runtime exclusions. Full guest backups retain those workspaces, standalone recovery helpers, and software rollback copies. The exact top-level exclusion preserves similarly named owner folders and nested workspace files.
