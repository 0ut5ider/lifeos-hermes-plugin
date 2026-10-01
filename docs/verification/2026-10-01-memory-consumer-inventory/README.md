# Native memory consumer inventory

Date: 2026-10-01. Branch: `feature/lifeos-memory`. Data is synthetic. Ownership remains disabled on running installations.

## Alternate Cortex canonical reader

The unchanged `probe_cortex_scope.py` reproduces a managed canonical read with no caller context. `cortex-scope-before.txt` records the exposed synthetic marker. This is a runtime result, not a text-search inference.

The managed canonical reader now requires unrestricted source authority before collection. It accepts only the installed memory root or its Knowledge directory. It constructs an ephemeral note from native frontmatter and registered current facts. The native Cortex parser retains record identifiers, types, provenance, query behavior, and output envelopes. Native files do not change. Forgotten and superseded sections do not enter the projection. Unknown sources need adoption first.

The reader checks current fact digests and physical paths. It refuses revoked callers, foreign roots, unclassified project-only grants, outside mutation, oversized files, and excluded dynamic metadata. Native schema keys, enums, and category directory names remain operational metadata. They do not become retired claims.

## Evidence

1. `canonical-before.txt` and `canonical-before-correct-query.txt` record the missing boundary. The first query also contains a fixture token mismatch.
2. `canonical-after.txt` and `canonical-metadata-after.txt` record the incorrect use of fact validation for frontmatter. The native validator reports frontmatter injection. Trimming whitespace does not fix that error.
3. `canonical-parser-after.txt` verifies the native canonical parser and exact declared source text.
4. `canonical-metadata-control-before.txt` and `canonical-directory-control-before.txt` reproduce fixed metadata exclusion errors.
5. `canonical-schema-after.txt` verifies the native field-schema correction.
6. `canonical-final.txt` passes 16 cases in 14.882 seconds without skips. It covers search, get, export, status, timeline, rebuild, correction, forgetting, revocation, roots, source integrity, and standalone behavior.
7. `preparation-final.txt` records ordered distributed source preparation. Both distributed memory patches contain the same bytes.

Pinned sources: Hermes `758ad514eb0e800547e015edf05aa18f78b78d82`; LifeOS `5e2f2e8c0abde612da0e99c16c0d07d4ec21b88c`. Prepared output: `source-gate-20261001-canonical-final`. This unit expands the existing native memory patch from 18 files to 19. It adds no Hermes patch group.

## Limits and open inventory

The canonical connector has a 3 MiB transport limit. This is smaller than Cortex's 128 MiB whole-corpus limit. Excess data receives an explicit unavailable result. This result does not establish maximum-size corpus parity. The alternate reader requires unrestricted owner recall because native note metadata has no project classification. Restricted project tools remain separate.

The candidate inventory contains 132 files. This unit does not close that inventory. Graph caches, wiki indexes, Knowledge queries, native dashboard file routes, restore, staged publication, and derived context still require their own checks. A source trace is not a live access test. Full PULSE UI and secure LAN browser tests remain separate from the localhost relay evidence.
