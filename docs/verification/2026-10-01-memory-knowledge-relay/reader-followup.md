# Native callers after the Knowledge read gate

Date: 2026-10-01. Source: the pinned prepared public LifeOS tree. This trace does not read an existing installation's memory or invoke its services.

## Current Knowledge page

`LIFEOS/PULSE/Observability/src/app/memory/knowledge/page.tsx` uses these routes:

| Line | Call | Managed evidence |
| --- | --- | --- |
| 148 | `/api/wiki/search` | Wiki search tests use authenticated current sources. |
| 357 | `/api/wiki` | Wiki index tests cover current notes, retained silos, and documentation. |
| 368 | `/api/wiki/knowledge/:category/:slug` | Wiki note tests cover current Knowledge bodies, correction, forget, and revocation. |

The page has no PUT, POST, textarea, or note-save call. `src/app/knowledge/page.tsx` redirects to this page. The whole-file Knowledge PUT exists in the Observability server and public API documentation, but no current TypeScript, TypeScript JSX, shell, or Python caller in hooks, skills, or LIFEOS invokes it. This is evidence about the shipped source, not a claim that external callers do not exist.

Managed Knowledge PUT remains blocked. A reviewed replacement must not be implemented as a blind frontend save. It must account for multiple current registered facts, their references and project grants, retained appended history, metadata, and derived indexes. The complete write behavior remains open. Existing fact correction and reviewed staged publication do not establish whole-note edit parity.

## Actual mount and update callers

`lifeos_hook_bridge/install_source.py::finalize_lifeos` invokes installed `LIFEOS/HERMES/Mount.ts`, then its `--check`. The installed native source resolves beside the actual HERMES module. `lifeos_hook_bridge/update_worker.py` runs that same mount during publication and verifies it after the gateway restarts.

`LIFEOS/HERMES/RenderSoul.ts` reads the constitution, assistant identity and memory, principal identity and memory, TELOS, and projects. `skillIndex()` also reads each mounted skill's SKILL.md frontmatter and supplies skill name and summary text to the prompt. These paths require more than hot-file recall. The next renderer tests must cover identity and goal text, skill metadata, exact physical source binding, correction and forget, missing caller authority, and generated prompt refresh.

The earlier [native probe](../2026-10-01-memory-wiki-relay/other-reader-boundaries.md) demonstrates that a raw renderer includes forgotten identity text and that the existing runtime guard refuses it. It does not prove a managed mount can produce a current permitted prompt. Install and update need live prepared-source outcomes in both connector states. The original 132-file inventory excludes HERMES and cannot serve as a complete source inventory.

## Documentation source limits

The wiki corpus probe admits 58 of 60 pinned documentation pages. Two native Memory documentation files contain literal private-boundary examples. They remain excluded. Static documentation and the system prompt also inherit the conservative retirement clock for unclassified sources. A complete source-publication design must distinguish verified code sources from mutable user sources without declaring an arbitrary path public. No exemption is implemented in this unit.
