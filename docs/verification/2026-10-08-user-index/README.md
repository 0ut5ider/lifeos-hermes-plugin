# Native user index admission

Date: 2026-10-08. The prepared source tree is the first user-index candidate. Bun is 1.3.14.

Managed GET /api/user-index uses the authenticated Life relay. The route accepts only the native full index and the stats, publish, stale, and gaps slices. Anonymous callers, revoked owner bindings, invalid bearer credentials, cross-origin requests, extra selectors, duplicate filters, and non-GET requests refuse access. Connector loss keeps the route closed.

The operation calculates the index from current admitted owner Markdown. It does not serve the existing cache. Native categories, collections, frontmatter inference, staleness, completeness, previews, domains, publication eligibility, and interview gaps retain their original calculations. Complete comparison normalizes only the generated_at field, which changes at each native calculation.

Discovery preserves the native directory exclusions and two-level directory traversal. It has a shared 2,048-entry limit. Each selected source has a 256 KiB limit. Source and response transport have a 3 MiB limit. The installed USER root alias must point at the exact physical owner store. Redirected child sources, hardlinks, registry aliases, unexpected file types, and different file owners refuse access. Non-Markdown files do not enter the index.

Current source validation and retirement checks govern bodies and labels. The old cache cannot restore a changed preview, private source, or retired source. Exact safe owner review can restore an older source without changing its bytes or timestamp. Known retired labels remain excluded from current files. Completed native rendering receives another source, directory-entry, and owner-authority check before delivery. Separate processes change a source, create a source, and revoke an owner after actual rendering. Each case withholds the response.

The baseline runs five cases in 5.095 seconds and reports nine failed assertions. It demonstrates raw cached disclosure and missing current-source admission. The first gate refuses the intended installed USER alias. Its direct probe identifies that boundary. The second gate also checks an unselected SQLite file. Its direct probe identifies the registry alias. The collector now checks the exact installed root and applies source file checks only to selected Markdown. It still checks traversed owner directories.

The third gate passes five cases in 8.035 seconds. The expanded gate passes eleven cases in 18.592 seconds with warnings treated as errors. The [adjacent gate](adjacent-gate.txt) passes 276 cases in 371.145 seconds. It has no skips and treats warnings as errors. Actual native preparation applies all 11 Hermes and 23 LifeOS patch groups. The dependency receipt verifies unchanged manifests and lockfiles before reusing dependencies.

The selected pinned Pulse source does not register the user-index publisher as a running module. The public program retains a manual CLI, exported lifecycle, and exported handler. Its publication boundary requires separate verification. The reader gate does not close that writer, the remaining native audit, installed ownership acceptance, or the combined release gate. This candidate is not deployed during these checks.
