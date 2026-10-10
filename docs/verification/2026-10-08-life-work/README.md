# Native local work admission

Date: 2026-10-08. The source tree uses the prepared local-work candidate and Bun 1.3.14.

Managed `/api/life/work` uses the fixed authenticated Life relay. This local view does not require the optional GitHub Work module. It renders the owner's project list, current focus, workstreams, and active algorithm sessions.

The operation admits four fixed sources: USER/PROJECTS.md, USER/TELOS/TELOS.md, USER/TELOS/CURRENT.md, and MEMORY/STATE/work.json. It checks the selected physical owner files, including missing-source state. Redirects, hardlinks, different file owners, registry aliases, and oversized sources refuse access. Source files have a 256 KiB limit. The collected content and decoded projection have a 3 MiB budget. Responses also have a 3 MiB limit.

Original and decoded JSON text receive native private-content validation and current retained-source checks. Old unreviewed sources remain subject to the existing retirement cutoff. Current retained files cannot restore an escaped retired session. Project references appear as native display text; the operation does not open referenced project directories or URLs.

The supplied-source renderer retains the native table and narrative project parsing, TELOS precedence, current-field parsing, active-session filtering, and display limits. Default callers retain their filesystem readers. Supplied-source rendering cannot reopen a file. Separate processes observe completed native rendering before changing a project, changing session JSON, creating a previously missing TELOS source, or removing the owner binding. Each change withholds the response.

The [first baseline](baseline.txt) reports seven failed assertions across eight tests. One preservation assertion uses a field format the native parser does not recognize. The corrected fixture puts the colon inside the bold field label. The [field baseline](field-baseline.txt) then reports six failed assertions. Complete native response comparisons pass for table projects, narrative projects, TELOS precedence, and empty state. The raw [first baseline archive](baseline.raw.txt.gz) and [field baseline archive](field-baseline.raw.txt.gz) preserve exact output. Their receipts record hashes and byte counts. Readable baselines remove trailing ASCII whitespace only.

The [first gate](first-gate.txt) and [expanded gate](expanded-gate.txt) identify a combined-fixture error. The test removes the connector, then checks account revocation while the connector is still unavailable. The [connector mode gate](connector-mode-gate.txt) restores its bytes but recreates the file with nonprivate permissions. The native connector correctly refuses that configuration. The fixture now restores the connector's bytes and private permissions before checking revocation separately. The [isolated correction](connector-correction.txt) passes that test.

The [final focused gate](final-gate.txt) passes 12 cases in 16.662 seconds with warnings treated as errors. It compares complete native responses and checks both private and retired decoded text. It also covers the native 20-project and ten-session limits, malformed JSON defaults, current Origin, bearer precedence, selectors, non-GET requests, source limits, hardlinks, connector loss, and source or authority changes after rendering.

The [first adjacent gate](adjacent-first.txt) runs 145 cases in 158.708 seconds. Its only failure is the connector fixture above. The [corrected adjacent gate](adjacent-gate.txt) passes all 145 cases in 154.598 seconds without skips and with warnings treated as errors. It records the neighboring Life, source, authority, native job, profile, patch, and ordered preparation checks. The [source identity](source-identity.json) and [dependency selection](dependency-selection.json) record exact code and unchanged dependency manifests. Both memory patch copies have identical bytes. Ordered preparation applies all 11 Hermes and 23 LifeOS patch groups.

Installed ownership acceptance, business views, source-review coverage for additional source classes, and user-index publication remain open. The candidate is not deployed to `.252` during this gate.
