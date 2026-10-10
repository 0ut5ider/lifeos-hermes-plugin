# Atlas initialization and fresh graph acceptance

The initialization code commit is `c775dcca61b9ae161e12e0e91d6f08da339f21a5`. The final planner guard commit is `ef946c3faac3c3faf27912992da526404ca290b0`. The branch starts from merged `main` at `38f5534628be21a62fea87553313b964282e8e8d`.

## Baseline and focused checks

The [baseline output](before.json) records four expected failures: two missing synchronization cases and two narrative destination changes that lose the recovery journal. The baseline also runs the three imported publication destination tests. The later suite imports that fixture as a module and does not collect those tests again.

The [final gate](final.json) passes all 80 selected tests in 129.009 seconds. Its request record binds the command, environment, and nine tested file hashes. The checks cover fresh and empty graphs, native reconciliation identities, incomplete observations, targeted and full sweeps, actual managed CLI routing, the explicit owner command, current authority, post-publication changes, process death, later edits, and recovery. Neighboring Atlas readers and narrative jobs also pass.

The [final directory guard gate](final-guard.json) passes all 81 selected tests in 128.961 seconds. Its recorded source hashes match the final guard commit. The [directory baseline](directory-before.json) fails because the inherited `ATLAS_DIR` creates an unrelated directory. The [focused repeat](directory-after.json) passes after the bridge binds its selected directory before module loading. The passing suite records a non-failing SQLite ResourceWarning from a test connection.

The [strict TypeScript check](native-types.json) passes the changed native Store, Atlas command, and bridge. The [configuration](native-types-config.json) retains strict mode. It uses the existing TypeScript dependency. The [final strict repeat](native-types-guard.json) also passes and binds the final bridge hash.

The earlier [neighbor run](neighbors.json) passes its 61 actual tests but also requests a nonexistent test module. Its result is a failure. The final gate uses `test_memory_publication_recovery` and passes cleanly. The intermediate Atlas outputs retain the fixture setup errors and their correction.

## Packages and installed selection

The [merged baseline build](fresh-text-candidate-merged-38f55346-build.json) verifies both complete native sources and produces a 341,535,229-byte archive. Its [installed validation](merged-candidate-installed.json) verifies all 199 plugin files, native manifests, version declarations, and the installed Hermes dependency inputs.

The [Atlas build](fresh-text-candidate-c775dcca-build.json) produces a 341,545,130-byte archive from the tested code commit. Its [installed validation](atlas-candidate-installed.json) verifies all 200 plugin files and both native manifests. Both packages retain eleven Hermes patches and 25 LifeOS patches. Both native pins remain unchanged.

The [selection operator](select_installed_candidate.py) drains only the synthetic acceptance services. It checks each previous file against the acceptance manifest. It retains previous bytes and file modes, selects the committed plugin files, and updates the installed and canonical Atlas files. It verifies the canonical source tree and both private configuration files before service restart. The [selection result](installed-candidate-selection.json) records all selected hashes and service state.

The [final guard build](fresh-text-candidate-ef946c3f-build.json) produces a 341,535,987-byte archive from `ef946c3f`. Its SHA-256 is `20d88d9f590f2e5e999db45aab28dea63057f11e86b135646eac09f4126f3fd7`. The [installed package validation](guard-candidate-installed.json) passes. The [guard selection](installed-guard-selection.json) retains the previous bridge bytes and verifies all 200 selected plugin files.

The acceptance stage is `/home/lifeos-hermes/migration/2026-10-09/daily-text-581d76a7`. The final selected package is the separate `daily-text-0.2.0-ef946c3f` stage. The live `.252` profile is outside this selection.

## Installed acceptance

The [installed operator](verify_installed_atlas.py) starts with no graph, snapshot, or narrative cache. It creates only synthetic Gear and Projects fixtures. It runs actual installed Hermes owner commands and actual authenticated Pulse requests. A loopback HTTP observer forwards real requests to the configured private endpoint. It records model and effort fields without prompts or credentials. The observer does not change the selected model configuration, provider URL, or tier mapping.

The first attempt creates and reads the graph. Its direct service call fails because the operator PATH does not include the installed Bun executable. A paired observation with the installed PATH makes that same call succeed. The operator sets the installed PATH for both direct calls and subprocesses.

The second attempt generates actual private model narratives. Its repeat check assumes that the explicit `atlas-insights` command reuses the cache. The native command intentionally regenerates on each invocation. The corrected repeat check reads the current dashboard insight and checks that the read preserves the cache and makes no new model request. Both attempts remain separately retained on `.252`.

The [complete installed acceptance](installed-atlas-verification.json) passes on `c775dcca`. It verifies three initial assets, four after a Gear source update, native reconciliation identities, one relationship, old-signature refusal, and current authenticated reads. Both actual model requests return HTTP 200 with model `flashnext-w4a16-fp8ple` and effort `xhigh`. The selected pin remains Fable. The four tier efforts and the exact model configuration bytes remain unchanged. Dashboard reads preserve the current narrative cache without inference. The explicit insight command regenerates by design.

Disabled ownership, a read-only owner grant, and an unmapped local account each refuse the actual sync command before artifact changes. Anonymous views return HTTP 401. A removed dashboard account returns HTTP 403. Restoring the account restores current reads. All three published artifacts have mode `0600`.

The actual installed interruption child exits with code 73 after database publication. The unknown receipt and publication journal remain present. Recovery restores the exact prior database, snapshot, and cache bytes as a group. The restored insight is current. Local later-edit tests refuse recovery while the later edit remains and preserve every group member.

The [installed final guard repeat](installed-guard-verification.json) passes after selecting `ef946c3f`. It runs the actual sync command with an inherited outside directory. That directory remains absent. Native asset identities, cache bytes, inode, modification time, and both configuration files remain unchanged. Both authenticated Atlas views return HTTP 200 and remain current. This repeat validates the guard delta; the complete fresh initialization and actual model generation run uses `c775dcca`.

The [live before](live-before.json) and [live after](live-after.json) operational metadata are exactly equal. Only the isolated acceptance profile receives code and synthetic graph artifacts.

## Browser evidence

The collaborative browser renders the populated [graph](atlas-graph.png) and [current narrative](atlas-insights.png). The [browser record](browser-atlas.json) retains visible text and HTTP 200 Atlas requests. No regeneration action runs during browser inspection. The first tunnel uses a different local Pulse port and receives the existing non-loopback Host refusal. Forwarding the original Pulse port succeeds without changing the guard. Existing missing-font and excluded Bunker route HTTP 404 responses remain recorded. This check does not claim an empty browser console.

## Retention and rollback

The original selection retains replaced files under the acceptance stage at `atlas-initialization-retained`. The final guard selection retains them at `atlas-selection-retained-ef946c3f`. Each directory contains the previous acceptance manifest, exact file bytes, and file modes. To undo the selection, drain only the three acceptance services, restore files from the retained map and the previous manifest, verify the restored selection, and resume those services. The live profile does not require rollback. The two unsuccessful acceptance attempts retain separate graph and operator artifacts on `.252`. Synthetic source changes belong only to this acceptance installation.

## Release boundaries

The owner command synchronizes admitted Gear and Projects sources. It uses native `Store.applyRun` and snapshot export. The planner closes and checkpoints its private database copy before publication. The live database uses SQLite DELETE journal mode so publication can replace one closed file. The database and snapshot have mode `0600` and share one recoverable publication group. Unexpected SQLite companion files cause refusal. The full database is bounded to two MiB. A larger database refuses synchronization. This gate verifies fresh personal Gear and Projects graphs; it does not establish long-term graph growth or a retention policy.

This change adds no Atlas timer. Managed `tick` refuses before consuming hints. The explicit owner command can initialize and refresh the graph. Standalone native tick behavior remains unchanged. Managed raw writers refuse; the Pulse readers continue through current owner admission.

The native graph remains outside USER_DATA. The existing USER_DATA profile backup does not preserve its synchronization and lifecycle history. The final guest backup and recovery gate must include `.local/state/lifeos/atlas` if that history must survive a guest restore. Rebuilding from retained Gear and Projects files restores current derived assets, with fresh history.

Private-channel setup follows daily-guest creation under Adrian's confirmed order. Channel and audience acceptance must precede bot cutover and lasting-memory activation on that guest. `.252` remains the development server. Daily deployment, combined release approval, and Discord channel acceptance remain open.

The task-owned collaborative browser tab and both temporary SSH forwarding processes are closed after inspection. No dashboard Host rule or live service setting changes.
