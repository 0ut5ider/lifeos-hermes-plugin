# Atlas limits, daily refresh, and grouped recovery

This gate follows the [independent Atlas limits review](../../agents/2026-10-10-atlas-limits-review/atlas-limits-review.md). The primary agent independently repeats the actual managed capacity, freshness, and native backup experiments. The [repeat results](../../agents/2026-10-10-atlas-limits-review/primary-verification/results.json) record two successful experiment commands with empty stderr. The [projection check](../../agents/2026-10-10-atlas-limits-review/primary-verification/projection-check.json) confirms 9,996 admitted fields and 10,026 refused fields.

## Changes

The native planner exports its complete private graph and snapshot before publication. Planned and live graphs share the same admission function. The owner operation checks source exclusion, retirement, complete projection, table rows, and byte limits while the planned files remain private. It preserves the existing checks for current authority, source versions, publication destinations, and post-publication admission.

The bounds remain two MiB for the database, 256 KiB per source or snapshot, 10,000 projected text fields, and 2,048 rows per graph table. Capacity results expose numeric counts, bytes, limits, and warnings at 80 percent. They do not include source text. An over-limit plan leaves live artifacts unchanged and creates no publication journal.

The daily profile runs `hermes lifeos-job atlas-sync` at 06:50 in America/Toronto. Dashboard narrative regeneration first runs the same governed sync. The command rechecks authority between native programs. Empty graphs remain idle and make no narrative model request. Atlas failure output passes through current owner admission before the command returns it.

The existing profile backup format remains unchanged. It omits the external graph and snapshot. The [daily VM recovery gate](../../deployment/daily-text/README.md#final-daily-vm-backup-and-recovery-gate) requires an off-server whole-guest backup and isolated restore before bot cutover. The [synthetic grouped restore tests](../../../tests/test_memory_atlas_guest_recovery.py) cover ordinary restoration, recovery after actual process death, and refusal to overwrite a later edit. They do not prove Proxmox disk coverage or a final daily VM restore.

## Local evidence

The [capacity baseline](before.json) records the expected failures before planned-state admission and capacity reporting. The [first passing gate](after.json) passes 23 tests. It retains three non-failing SQLite ResourceWarnings from test connections that the final change closes.

The [first refresh baseline](refresh-before.json) includes a fixture configuration error. The [corrected characterization](refresh-characterized.json) reproduces missing initialization, missing failure diagnostics, and unchanged graph assets after source edits. The [refresh gate](refresh-after.json) passes 17 tests through actual native owner programs and the native Pulse job loader. Model responses in these local tests come from a controlled synthetic loopback endpoint.

The [grouped recovery gate](guest-recovery.json) passes three tests. It copies and restores complete synthetic filesystem groups at their selected paths. The actual interrupted publication process exits with code 73. Normal owner recovery restores every original artifact. A later edit prevents replacement of every group member and preserves the journal.

The [first combined run](combined-before-fixture-correction.json) records three failed tests. The [fixture characterization](gate-failure-causes.json) proves that the exclusion test instruments an unused instance. It also proves that the shutdown fixtures contain raw WAL companion files and correctly refuse before inference. The corrected exclusion test observes the actual service instance. The shutdown fixtures initialize through governed sync instead of seeding an open raw graph. These fixture changes preserve the runtime's companion-file refusal.

The [focused correction gate](fixture-correction.json) and [combined regression gate](final.json) record their commands, environments, source hashes, durations, and complete output. The combined gate includes neighboring Atlas readers, narrative jobs, owner commands, publication recovery, operational views, daily configuration, and patch mirror checks. The [strict TypeScript check](native-types.json) validates the changed native Store, Atlas command, Pulse Atlas module, and bridge. The [native preparation record](native-refresh-preparation.json) binds all 25 LifeOS patches before test dependencies are linked.

The focused correction gate passes all three tests. The final combined gate passes all 124 selected tests in 373.906 seconds, with no ResourceWarnings. Every recorded source hash matches the committed code and tests. No whole-repository test run is claimed.

## Installed acceptance and release boundary

The code commit is `5163a0ceb9c570c9fd8b1f865954e6aad508f367`. The [candidate build](fresh-text-candidate-5163a0ce-build.json) verifies both complete native sources and all 200 plugin files. It retains eleven Hermes patches, 25 LifeOS patches, and both selected native pins. Its archive contains 341,556,310 bytes with SHA-256 `3bb3b555f7ae3a0cc0997bb3409fd4e68d54486437122df470b7833302ff6b4a`. The [tested candidate identity](tested-candidate-identity.json) matches nineteen recorded test and strict-check hashes to the packaged files.

The [archive verification](archive-installed.json) and [installed package validation](candidate-installed.json) pass on `.252`. They verify the transported archive, all declared plugin and daily configuration files, both complete native manifests, and installed Hermes dependency inputs. The [isolated selection](installed-candidate-selection.json) retains and replaces thirteen files, including the daily profile. Both configuration files and model routes remain unchanged.

The [installed operator](verify_installed_limits.py) uses only the synthetic acceptance profile on `.252`. The [first installed attempt](installed-first.json) passes capacity refusal but stops because its loader points to the dependency-free canonical source tree. The [error](installed-first.stderr) records the missing `smol-toml` package. The corrected operator verifies that the installed and canonical Pulse loaders have identical bytes, then uses the installed loader and its existing dependencies. It makes no dependency or native program change for this correction.

The [complete installed acceptance](installed-verification.json) passes. It checks over-limit refusal without changing the graph, snapshot, or cache and without a publication journal. The actual native loader spawns the selected daily sync command. Narrative regeneration reconciles a changed synthetic Gear source before one real private model request. That request returns HTTP 200 with `flashnext-w4a16-fp8ple` and effort `xhigh`. Both authenticated Atlas views return HTTP 200 and show the current narrative. Disabled ownership refuses before artifact changes. All three artifacts retain mode `0600`.

The selected pin remains Fable. The efforts remain Haiku `low`, Sonnet `medium`, Opus `xhigh`, and Fable `xhigh`. The exact model configuration SHA-256 remains `db397e27d76475e121fbe333dde75a6b2a21539c9aa2757676c2c1f113049a20`. The completion marker contains zero and the installed stderr file is empty. The first attempt and its output remain separately retained in the acceptance stage.

The selection operator retains previous bytes, modes, and the acceptance manifest under `atlas-selection-retained-<commit>` in the isolated acceptance stage. Rollback drains only the three acceptance services, restores the retained files and manifest, verifies the selection, and resumes those services. Synthetic Gear changes remain within this acceptance installation.

The [live before](live-before.json) and [live after](live-after.json) service and configuration metadata match exactly. The live profile retains disabled ownership and sharing. The new daily VM, its off-server backup and restore, private Discord channel audience, bot cutover, and lasting-memory activation remain open. Channel setup follows daily VM creation under Adrian's confirmed order. Automated Atlas history retention remains a recorded follow-up. The first release uses bounded admission, capacity diagnostics, and a reviewed retained rebuild.
