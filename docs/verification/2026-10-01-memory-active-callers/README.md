# Native callers and prompt publication

Date: 2026-10-01. Role: primary implementation and verification.

## Source inventory

The inventory scans 1,579 public source files. It retains the preceding 132 candidates and expands discovery to the whole install tree. It excludes dependencies, build outputs, test trees, symlinks, USER, and MEMORY. It does not read installation data or shared memory records.

The scan records 227 candidates:

| Disposition | Files | Meaning |
| --- | ---: | --- |
| Registered hook | 29 | The native hook manifest names the file. This count represents distinct files, not hook registrations. |
| Declared entry | 142 | The source provides a CLI, server, scheduled command, framework page, or documented watcher entry. This does not prove that a running installation enables the entry. |
| Imported from entry | 48 | A resolved source import connects the file to a declared entry. Conditional imports still require runtime configuration. |
| Configuration or documentation data | 6 | The file supplies configuration or reference data. It is not an executable caller. |
| Exported utility without active caller | 2 | No active caller appears in the scanned source. |

The two utilities are `PULSE/edit/edit-handler.ts` and `PULSE/lib/provenance-watcher.ts`. Their exports do not establish a production edit route. Explicit support or refusal still needs a behavior test before ownership activation.

The whole-tree pass adds the terminal status line and Kitty watcher. It also adds the root settings templates and a documentation rename map. These files were outside the preceding five directory scopes.

[caller-inventory.json](caller-inventory.json) records source identities, resolved callers, entry dispositions, source references, and policy-review status. [trace_callers.py](trace_callers.py) reproduces the resolved import pass. [manual-entrypoints.json](manual-entrypoints.json) records entry points confirmed by primary source inspection. The script uses the preceding [source-traces.json](source-traces.json) as its seed and preserves candidates that do not contain the expanded search terms.

The initial filename-reference search produces false callers, especially for `page.tsx` and `module.ts`. Those references remain in raw evidence. The resolved inventory does not use those filename matches as import evidence.

An import reference is source evidence. It is not a runtime trace or a TypeScript compiler reachability result. The inventory does not discover arbitrary external scripts, computed plugin extensions, user-added schedules, or a running installation's module selection. Its `contains_governed_api_reference` flag identifies a review candidate. It does not prove policy coverage.

## Actual prompt and publication callers

| Caller | Source or output | Required work |
| --- | --- | --- |
| Plugin `finalize_lifeos`, update worker `_runtime`, native `Services.ts`, PULSE `modules/hermes.ts` remount | `HERMES/Mount.ts` and `HERMES/RenderSoul.ts`; constitution, identity, goals, projects, hot facts, and skill metadata become `SOUL.md` | Govern collection and prompt publication. This unit implements the conversation-bound mount and owner publication API. Administrative install and update integration remains open. |
| Direct `TOOLS/RenderHermesSoul.ts` CLI | Separate prompt formatter and workspace output | Preserve its own native format or refuse it under managed ownership. It does not replace the active mount renderer. |
| `InstallDerivedSync.ts` and direct `DerivedSync.ts` CLI | USER source changes regenerate derived artifacts | Govern inputs, preserve output provenance, and verify each native action. |
| Direct `KnowledgeDistill`, `KnowledgeGraph`, and `MemoryGraph` CLIs | Canonical notes become digests and graphs | Bind inputs and derivatives to current registered records. Raw indexes cannot establish current facts. |
| PULSE `AdapterCli`, `RebuildAll`, and `SnapshotPages` | Adapter inputs become `PULSE_DATA` and snapshots | Separate operational metadata from retained facts. Verify model inputs and publication destinations. |
| Learning and Wisdom synthesis CLIs and scheduled commands | Retained observations become summaries, hypotheses, and frame updates | Apply current retirement and project policy before inference and publication. |
| Native PULSE modules and Observability routes | USER, work state, retained bodies, and derived caches reach HTTP responses | Preserve supported owner views. Test or refuse each remaining read and write route. |
| Registered hooks and their imported helpers | Current facts, retained observations, operational state, and transcripts reach hook context or logs | Use the existing paired outcomes where available. Close uncovered source and writer paths with native fixtures. |

The existing canonical, recovery, staging, diagnostic, wiki, and Knowledge tests remain separate coverage evidence. This inventory does not declare their unrelated consumers complete.

## Implemented prompt contract

The active native formatter accepts declared text and skill sources. It preserves native section extraction, budgets, path scrubbing, output-format selection, skill parsing, and final output validation. Its declared renderer does not reopen identity or memory files.

The plugin selects the five fixed constitution and identity sources, installed top-level `SKILL.md` files, and both registered current hot snapshots. One cooperating memory transaction covers collection and formatting. The collector validates bodies and source labels, applies retirement policy, and rechecks source text after the native worker returns.

Missing context, restricted recall, invalid physical paths, private markup, and connector failures do not permit raw fallback. The native exported read helpers also use the connector. Standalone LifeOS preserves its existing behavior when no connector is installed.

The mount uses one admitted bundle for the prompt, launcher policy name, and skill count. A managed mount refuses an unavailable launcher name. It cannot silently remove the launcher denial because identity was excluded.

## Publication contract

The authenticated owner API provides:

1. `POST /memory/prompt/preview` with `keep_output_format`.
2. `POST /memory/prompt` with `signature`, `previous_digest`, and `keep_output_format`.

The native mount uses corresponding conversation-bound connector operations. The connector binds the destination to its configured Hermes profile. Callers cannot select another output path.

The signature binds admitted sources, current hot entries, retirement metadata, scope, options, rendered output, and installation. Publication collects again and checks the signature. It rechecks current configuration authority. A separate destination digest protects a later `SOUL.md` edit. A matching output makes retry return `unchanged`.

The plugin uses the existing atomic file publisher. It writes a private temporary file, flushes the file, replaces `SOUL.md`, and flushes its directory. The published file has mode 0600. Matching text does not preserve an existing public file mode. This is an atomic single-file publication. It does not make the native mount's configuration, plugin policy, and environment changes one recoverable transaction.

## Test evidence

The preceding implementation passes the standalone formatter characterization but fails managed missing-context admission and declared-source rendering. [prompt-before.txt](prompt-before.txt) preserves those failures. The first paired hot-fact test detects an added bullet prefix. The implementation preserves the native line format.

Publication tests initially fail because the owner controls are absent. [publication-before.txt](publication-before.txt) preserves that failure. A controlled interleaving then reproduces source mutation during native formatting. [source-race-before.txt](source-race-before.txt) records the failure; [source-race-after.txt](source-race-after.txt) verifies source and owner-revocation checks. These interleavings call the real native worker and inject the competing change at its return boundary.

[launcher-before.txt](launcher-before.txt) reproduces a mount that removes the launcher denial when identity is excluded. The final distributed gate includes the refusal regression.

The pinned public constitution produces the same governed and standalone bundle. [public-constitution.txt](public-constitution.txt) records that test.

[gate-with-unrelated-host-tests.txt](gate-with-unrelated-host-tests.txt) records an initial 134-case run with two unrelated installed-hook tests skipped. The relevant gate excludes that host-only module. [gate-before-launcher-refusal.txt](gate-before-launcher-refusal.txt) records 133 passing cases before the last mount refusal. [gate-before-private-permissions.txt](gate-before-private-permissions.txt) records 134 passing cases before the last permission correction. [permissions-before.txt](permissions-before.txt) reproduces matching text retaining mode 0644. [permissions-after.txt](permissions-after.txt) verifies private publication. The final [gate.txt](gate.txt) and [gate.done](gate.done) record the current distributed result. [run_gate.sh](run_gate.sh) records its environment and command.

## Source versions and limits

- Hermes base: `758ad514eb0e800547e015edf05aa18f78b78d82`.
- LifeOS base: `5e2f2e8c0abde612da0e99c16c0d07d4ec21b88c`.
- Inventory source: prepared Knowledge-relay closure snapshot.
- Final test source: fresh prepared prompt-publication snapshot.
- Native memory patch: 27 files. The bundle still has nine Hermes and ten LifeOS patch groups.

Unclassified source age remains conservative. After retirement, an older constitution can require source review even when it contains no matching retired claim. The plugin refuses generation in that case. It does not alter timestamps or waive retirement checks. Reviewed code-source classification remains required.

Automatic prompt reconstruction on resume, administrative install and update authority, PULSE remount authentication, the alternate renderer, derived publication, restricted delivery, lifecycle, recoverable ownership, and the full release gate remain open. No running installation activates memory ownership. No server deployment occurs in this unit.
