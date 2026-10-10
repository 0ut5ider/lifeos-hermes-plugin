# Governed native tab freshness

Date: 2026-10-08. The candidate remains staged. These cases use synthetic sources, the actual native renderer, and authenticated Hermes HTTP sessions.

The [baseline](baseline.txt) passes the native field comparison and fails four tests. Anonymous callers read metadata. Revoked owners reuse cached metadata. A changed review date remains cached. A private source publishes its review date.

Managed tab requests now use the fixed authenticated owner relay. The collector uses the native tab registry and preserves the native date preference, labels, per-file fields, freshness tiers, and empty-directory fallback. It collects current bounded owner sources, validates their content and labels, excludes private and retired sources, and supplies source bytes and timestamps to the native renderer. The renderer does not reopen files. The collector rechecks source bytes, timestamps, directory entries, and account authority after rendering.

The collector permits the fixed installed sources and the two fixed local Atlas metadata paths. Regular text sources have a 256 KiB file limit. Collection has a 2,048-entry discovery limit and a 3 MiB transport limit. Atlas database metadata uses its checked file timestamp without reading database rows. Redirected sources and hard links refuse the view. Managed requests bypass the standalone cache and return `Cache-Control: no-store`.

Knowledge filenames can contain claims. Their metadata requires the existing current canonical source admission. Unregistered Knowledge notes remain on disk and do not appear in the freshness response. Retired source labels remain excluded. Empty directories retain their native directory timestamp. A directory that contains only excluded notes returns unknown metadata instead of publishing its timestamp.

The [focused gate](final-gate.txt) passes 18 tests with warnings treated as errors. It compares all 20 registered tabs in the synthetic installation. It compares expanded Markdown, JSON, and YAML sources, empty directories, and a directory with a qualifying nonfile child. It checks anonymous and revoked owners, connector loss, changed source bytes and timestamps after actual rendering, changed authority, private Markdown and JSON, retired labels, redirected files, hard links, byte limits, origin checks, bearer credentials, methods, and bounded selectors. A registered Knowledge control preserves native metadata.

The [first gate](first-gate.txt) passes five tests. The [expanded gate](expanded-gate.txt) finds one native fallback mismatch. The collector now tests qualifying regular children before choosing the directory fallback. The [directory gate](directory-gate.txt) passes all 11 cases. The [sixteen-case gate](sixteen-case-gate.txt) passes the additional boundary cases. The [Knowledge baseline](knowledge-baseline.txt) reproduces an unregistered filename exposure and passes the registered-source control. The canonical admission closes that exposure.

The [adjacent gate](adjacent-gate.txt) passes 174 tests in 224.969 seconds with warnings treated as errors. It includes combined upgrades, hypotheses, wiki, Knowledge, freshness, canonical recall, native HTTP, Pulse, preferences, source reads, and dashboard authority. The [preceding run](adjacent-control-source-error.txt) passes 169 cases and records five errors because the runner omits the native freshness control path. The corrected runner supplies the pinned control explicitly. Both outputs and completion statuses remain retained.

The dependency receipts compare manifests and frozen locks before selecting accepted dependencies. The source receipt records product and native hashes. Both patch copies have identical bytes. The repository defines no native TypeScript lint, typecheck, or build script for this module; this gate does not claim those checks.

These cases close the tested tab metadata boundary. They do not establish complete native caller coverage, full populated dashboard behavior, installed ownership acceptance, or daily-server activation. `.252` retains its deployed baseline.
