# Patch the existing Hermes installation

Decision date: 2026-10-17. Status: accepted architecture, implementation and installed qualification pending.

The installer must use the owner's existing Hermes installation. It must check compatibility before it offers installation. It must refuse an unsupported installation with a specific reason and leave active programs unchanged.

Adrian selects this design to preserve existing tools, plugins, dependencies, and configuration. An isolated replacement Hermes runtime is not an installation option or a fallback. Temporary source copies can support preparation and tests, but they must not become the selected Hermes runtime.

The published [0.7.3 workflow](installation-workflow.md) still installs a complete managed runtime. This plan does not change that release or establish that in-place installation is available today.

## Installation contract

1. The user installs the small release-manager plugin through the Hermes Plugins page.
2. The plugin identifies the running Hermes source, interpreter, profile, services, and version.
3. The plugin checks that installation against an explicit qualified compatibility entry.
4. The page displays whether installation is possible, the checked identity, and any blocking reason.
5. For a compatible installation, the user selects **Install LifeOS**.
6. The plugin downloads verified LifeOS and integration components and prepares the patch transaction.
7. The owner reviews the files, configuration keys, dependency additions, and required service interruption.
8. The installer rechecks the installation under its locks and stops all admitted source consumers.
9. The installer patches the existing Hermes source and installs LifeOS without replacing Hermes or its environment.
10. The installer restarts the admitted consumers and verifies the integration and preserved capabilities.

Preparation must not change active programs. Downloading or preparing LifeOS does not import personal data or activate memory ownership. Those actions retain their separate owner controls.

The bootstrap must remain usable on the qualified stock host before the bridge's required hooks exist. It must not report a complete installation when only a reduced set of hooks registers.

## Compatibility admission

A version label helps the user understand the result. It is not sufficient evidence of compatibility. Each release must declare the exact upstream revisions, supported layouts, source identities, dependency requirements, patch identities, and capability checks it qualifies.

The first implementation target is a user-owned Linux Git installation at an exact qualified upstream commit. The current source proof uses Hermes `v0.21.7`, commit `71d34bad1045610252eda02ee79549436896e784`. That proof does not qualify the new installer. Additional versions and layouts require their own entries and tests.

| Detected state | Required result |
| --- | --- |
| Exact qualified base, matching source, compatible dependencies, controllable consumers | Allow preparation and owner review |
| Exact recorded integration, matching journal and installed files | Report installed; offer only qualified update or removal actions |
| Older or newer Hermes without a qualified entry | Refuse; display the detected version and supported versions |
| Local source edits, partial patches, or unknown patch identity | Refuse; identify the conflict without overwriting it |
| Required dependency would replace an existing incompatible package | Refuse; explain the dependency conflict |
| Read-only, foreign-owned, or unqualified installation layout | Refuse; identify the unsupported layout |
| Shared checkout or active consumer that cannot be coordinated | Refuse; explain the consumer or profile boundary |
| Source or configuration changes after preparation | Invalidate the prepared operation and require a new review |

The installer must resolve the source actually imported by the running interpreter. It must check the Git revision, qualified source hashes, interpreter, installed dependency versions, and required host capabilities. A successful `git apply --check` is only one check.

Installed tools, skills, plugins, extras, model choices, credentials, and user data remain in their current locations. The installer must record their relevant identities and inventory before and after the transaction. It must distinguish user plugin files from upstream source when it checks drift. It must reject conflicts with patch targets, imports, or dependencies.

The installer must not silently remove, upgrade, downgrade, or replace existing dependency packages. It can add declared missing dependencies only when the reviewed plan proves compatibility and records the changes for recovery. Unsupported dependency combinations must produce a refusal.

An inventory cannot prove that every third-party plugin behaves correctly. Qualification must include representative tools and plugins, plus checks for the installed extensions that the host can exercise. The page must state the tested scope and report known conflicts.

## Component downloads

The GitHub plugin installation must contain the bootstrap, not a complete Hermes distribution. Activation must fetch the exact pinned LifeOS source and apply the canonical LifeOS patches. It must verify the resulting source identity before publication.

Release metadata must bind the integration files, patch files, LifeOS source, generated capability record, dependency inputs, and any required frontend assets to their hashes. Repeated operations can reuse verified cached components. A cache hit must receive the same integrity checks as a download.

Use the canonical patches in `lifeos_hook_bridge/patches/`. Resolve the [development patch-copy difference](../TODO.md#documentation-audit-follow-ups) before qualifying a second preparation path. Fetch the declared LifeOS commit directly; installation must not depend on upstream HEAD remaining at that commit.

Do not download a complete replacement Hermes or a stock Hermes recovery archive. Recovery must retain the actual original files from this installation. LifeOS still needs its own source and runtime components. Download size is not established until the component release exists and its network transfers are measured.

## Apply, update, and recovery

Use a durable transaction with exact before and after hashes, permission metadata, owned paths, and an interrupted-operation journal. Save original files before mutation. Flush files and journal state to disk before publishing each transition. Do not replace the Hermes checkout, interpreter, environment, public launchers, or unrelated plugin directories.

The detached worker must coordinate the installation lock and Hermes updater lock. It must enumerate all consumers of the same source, including the dashboard, gateway, command-line sessions, scheduled workers, and other profiles. It must stop or drain supported consumers and refuse an uncontrolled consumer. It must preserve each service's prior enabled and running state.

After restart, verify the new processes import the patched source and expose the required admission, lifecycle, and delivery controls. Verify preserved tools, plugin registrations, model configuration, and memory authority. A running gateway and a valid configuration file alone do not prove success.

The supported Hermes update command must coordinate with installed LifeOS patches. It must refuse an unqualified upstream transition or use a separately qualified transition transaction. It must not silently stash patches onto an unknown base or park them after conflicts. Direct external source edits remain detectable drift; the installer cannot prevent an owner from changing files outside its workflow.

**Update LifeOS** and **Update plugin** remain owner-visible actions. Each action must show which components and host patches change. An update must move between recorded qualified states without replacing Hermes. A host-version transition needs its own compatibility entry and verification; otherwise the update must refuse it.

Removal must restore the original host file contents and modes from the installation journal. It must remove only unchanged files owned by the integration and restore only recorded configuration keys. If the owner changes a patch target later, removal must stop and explain the conflict. It must not apply a blind reverse patch or restore a newly downloaded stock runtime.

Memory return, export, and ownership changes retain their separate workflows. Software removal must not erase personal data or silently select another memory provider.

Existing managed-runtime installations, including development and daily, need a separately tested transition. Their current selected Hermes can be the in-place target only after its identity and layout pass admission. The transition must not select another runtime or pretend that an unrecorded original installation can be restored.

## Implementation and acceptance order

These steps form one release. Passing an early step does not authorize deployment of a partial installer.

1. **Compatibility and bootstrap.** Add the compatibility manifest, read-only detector, and clear page results. Test supported, unsupported, edited, partially patched, shared, and read-only installations. Verify that refusal leaves programs and configuration unchanged.
   Status 2026-10-17: the detector, manifest generator, command, and page result are implemented on `feature/minimal-install-review`. The [host compatibility record](verification/2026-10-17-host-compatibility/README.md) lists the tests and the read-only results on three real hosts. **Install LifeOS** does not use the result yet; that gate belongs with the in-place transaction.
2. **Component preparation.** Add pinned LifeOS acquisition and verified component caching. Reproduce the exact qualified Hermes and LifeOS source identities. Test changed upstream HEAD, bad hashes, missing components, interrupted downloads, and cache reuse.
3. **In-place transaction.** Adapt the existing patch machinery to durable file recovery and all-consumer coordination. Test real services, concurrent update admission, later edits, stale review, and interruption at each journal state. Prove that Hermes and its interpreter retain their original locations.
4. **Update and removal.** Implement qualified patch transitions, upstream update coordination, and original-file restoration. Test idempotent operations, conflicts, failure rollback, service-state restoration, and memory ownership preservation.
5. **Installed qualification.** Test the GitHub URL and actual dashboard buttons on disposable existing installations with extra tools, plugins, dependencies, and profiles. Include representative incompatible extensions and an existing managed-release transition. Use real services and recovery paths; stubbed callbacks do not satisfy this gate.
6. **Review and release.** Complete independent review, fix findings, and qualify the exact component release. Update the public installation and recovery guides. Deploy development before daily after the whole release passes.

## Evidence and implementation gaps

The [primary verification](agents/2026-10-16-minimal-install-review/primary-verification.md) records exact Hermes and LifeOS source derivation. It also records that patches can apply over an outside-context local edit. These observations support source reconstruction and the need for stronger admission checks.

The current `lifeos_hook_bridge/install_source.py` supplies staged patch, restore, and recovery primitives. Its worker coordinates only the gateway and its patch journal lacks the durable publication guarantees required here. The current release manager prepares and selects a replacement runtime. Its removal path prepares stock Hermes. Those paths require implementation changes before they meet this plan.

The existing `optional/lifeos_release_manager/release_programs.py` provides durable publication and drift checks that can inform the file transaction. Reuse its applicable guarantees without replacing the host directory. Existing unit tests and source derivation do not establish real-service safety or third-party compatibility.

The [Opus review](agents/2026-10-16-minimal-install-review/minimal-install-review.md) remains the original alternatives analysis. Its private-runtime recommendation is superseded by this owner decision. Its measured updater, consumer, dependency, and recovery risks remain acceptance requirements.
