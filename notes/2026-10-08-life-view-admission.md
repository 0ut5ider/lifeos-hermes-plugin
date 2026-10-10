# Life dashboard routes can remain raw inside a governed file

2026-10-08, native caller review. The observability source already imports `MemoryAccess` for Knowledge routes. That reference does not govern its Life routes. The file still returns raw TELOS text from Life home, goals, and the Life-card alias.

The actual native HTTP baseline fails 11 assertions across eight cases. Anonymous and revoked callers receive goals. Private and forgotten source text reaches response bodies. Native field and fallback comparisons pass, which separates the policy defect from parsing behavior.

The correction supplies current admitted TELOS text to the existing native parsers. The fixed authenticated relay rechecks owner binding and source bytes after rendering. Fourteen focused cases pass, including correction, forgetting, connector loss, changed authority, redirects, hardlinks, and byte limits. The evidence is in `docs/verification/2026-10-08-life-views/`.

A file-level governed API reference is discovery evidence. It is not a complete route classification. Other Life routes and publication paths still need their own review.
