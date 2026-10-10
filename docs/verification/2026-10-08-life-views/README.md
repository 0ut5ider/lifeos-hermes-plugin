# Native Life home and goals admission

Date: 2026-10-08. The source tree uses the prepared Life-view candidate.

Managed `/api/life/home`, `/api/life/goals`, and `/api/observability/life-card` require an authenticated current owner session. The routes accept GET without selectors and refuse a foreign Origin. Ambient owner headers and internal process flags do not authorize an HTTP caller. The durable managed marker prevents connector loss from restoring raw reads.

The owner operation collects 24 fixed TELOS sources through the existing retained-source policy. It requires unrestricted owner recall. Sources must use the selected physical owner boundary. Redirects, hardlinks, non-files, oversized sources, and invalid source paths refuse. The collection excludes private, corrected, and forgotten text before native rendering.

The native handlers keep their parsing rules and response fields. Their supplied-source form retains unified TELOS precedence and per-file fallback. The home view retains current-domain summaries, next actions, goal limits, spark selection, and timeline counts. The goals view retains native sections, lists, and master text. Default native callers retain their existing file reader.

The owner operation rechecks source bytes and current account binding after rendering. The authenticated dashboard also checks the response binding before delivery. Retained-content checks and the response byte limit apply to the complete result. Requests use fixed routes and cannot select a different installation or source path.

The [baseline](baseline.txt) fails 11 assertions across eight tests. Anonymous and revoked callers receive goals. Private and forgotten text reaches native responses. Native field and fallback comparisons pass. The [first gate](first-gate.txt) passes all eight tests. The [expanded gate](expanded-gate.txt) passes 12 tests. The [final gate](final-gate.txt) passes 14 tests in 21.457 seconds with warnings treated as errors.

The readable baseline removes trailing spaces from two test-progress lines. The [lossless raw archive](baseline.raw.txt.gz) retains the exact process output. Its [receipt](baseline-archive.json) records the original hash and the normalization.

Tests use actual native HTTP listeners and actual authenticated dashboard sessions. Separate processes observe completed native rendering before changing a source or the account binding. The resulting response is withheld. Other cases cover correction, forgetting, connector loss, source byte limits, source redirects, hardlinks, query refusal, method refusal, and foreign Origin refusal.

The [adjacent gate](adjacent-gate.txt) runs 216 cases in 250.982 seconds. It passes 215 cases and skips the real-source preparation case because repository variables are absent. The [separate preparation gate](source-preparation-gate.txt) then runs that exact skipped case with both repositories configured. It passes and verifies every ordered patch, source whitespace, and the prepared Hermes resident-runtime import. The runner now includes both variables. All 216 selected cases have passing evidence. The original skip remains visible.

The [source identity](source-identity.json) records product, native, patch, and test hashes. The [dependency selection](dependency-selection.json) reuses accepted dependencies only after exact manifest and lock comparison. Preparation applies all 11 Hermes and 23 LifeOS patch groups. Both packaged memory patches have identical bytes. The native source has no configured lint, typecheck, or build script for this change.

This gate covers the three named read routes. Other Life routes, TELOS publication, user-index publication, installed ownership activation, and combined release acceptance remain open. No candidate program or configuration is deployed to `.252` during this gate.
