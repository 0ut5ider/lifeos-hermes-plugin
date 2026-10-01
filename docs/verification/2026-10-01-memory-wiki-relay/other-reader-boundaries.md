# Native consumers after the wiki Knowledge gate

Date: 2026-10-01. Source: the prepared public LifeOS tree used by the wiki regression. The [probe](probe_other_readers.py) creates only synthetic records and private disposable profiles. It runs real native HTTP handlers on localhost. It does not run sidecar remounts, model requests, or installed services.

## Measured open boundaries

| Native path | Current route or consumer | Actual outcome |
| --- | --- | --- |
| `PULSE/Observability/observability.ts` | Anonymous `/api/knowledge` | Status 200. The index includes an unregistered note title. The response has no storage restriction. |
| `PULSE/Observability/observability.ts` | Anonymous `/api/knowledge/research/SLUG` | Status 200 before and after a committed forget. The latter body retains the forgotten claim. |
| `PULSE/Observability/observability.ts` | Direct exported handler for `/api/memory/graph` | Status 200. A synthetic cached graph retains a forgotten title. The normal PULSE dispatch reaches the governed memory module first, so this direct-handler result does not prove that normal dispatch exposes this graph. |
| `PULSE/Observability/observability.ts` | Anonymous note PUT | Status 200. The exact unreviewed body replaces the native note. No registered current reference establishes this write. |
| `PULSE/modules/hermes.ts` | Anonymous `/api/hermes/file/principal-memory` | Status 200. The response includes current raw hot-memory text and file metadata. |
| `PULSE/modules/hermes.ts` | Anonymous hot-memory PUT | Status 200. The module makes one raw backup and replaces the current file. A lookup of the previously saved reference raises `MemoryConflict`. The registry detects the mismatch; the write does not use its transaction. |
| `LIFEOS/HERMES/RenderSoul.ts` | Native renderer with the managed connector present and no caller context | The renderer exits 0. It includes the current hot claim and a forgotten claim retained in the identity file. |
| Plugin `MemoryRuntime._rendered_prompt` | The exact generated SOUL text | The existing guard refuses the removed or superseded claim. This is guard-helper evidence. Existing runtime regression cases also cover fresh-session refusal. The renderer result does not prove that a permitted model request receives the forgotten claim. |

Full responses and written synthetic bytes are in [the captured data](other-readers-before.json). [Native process output](other-reader-process.txt) is empty. The probe exits 0 after capturing the expected reference conflict.

## Actual mount path

`lifeos_hook_bridge/install_source.py` runs installed `LIFEOS/HERMES/Mount.ts`. `update_worker.py` also runs that mount and its check. `Mount.ts` imports `renderSoul` from the adjacent `RenderSoul.ts`, then writes the result to the configured Hermes `SOUL.md`.

This is distinct from `LIFEOS/TOOLS/RenderHermesSoul.ts`. The original candidate scan covers hooks, TOOLS, and PULSE. It excludes the HERMES directory. Complete inventory work must therefore include HERMES and follow the install and update callers. The 132-file count does not describe the complete candidate universe.

Both native renderers anchor sources to their own physical module location. This probe physically copies the public HERMES module directory into the disposable install. A symlink to the source checkout would select the wrong USER tree and invalidate the observation.

## Follow-up order

1. Extend wiki source collection to the native retained silos and documentation with explicit physical-source and retirement tests.
2. Give the Observability Knowledge readers authenticated admission and declared current source rendering. Govern editing through reviewed current references.
3. Govern the actual HERMES mount renderer and its identity and skill metadata inputs. Verify prompt refresh, generation changes, and install and update callers.
4. Govern native sidecar source reads, reviewed writes, raw backup readers, and remount publication.
5. Complete graph and derived-source publication, including cached reads after correction and forget.
6. Trace the remaining original candidates and the directories outside the original scan. Bind each relevant caller to behavioral evidence.

These are measured development gaps. The plugin keeps memory ownership disabled until complete source coverage, restricted delivery, lifecycle, recoverable setup, and the full release review pass.
