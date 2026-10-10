# Native business admission

Date: 2026-10-08. The source tree uses the prepared business-view candidate and Bun 1.3.14.

Managed `/api/life/business` uses the fixed authenticated Life relay. It requires current owner recall. Anonymous requests, revoked accounts, foreign Origin, invalid bearer credentials, non-GET requests, and source selectors refuse access. Connector loss keeps the managed route closed.

The operation discovers companies under USER/WORK/YOUR_COMPANIES. It preserves the native preference for a company with a REVENUE directory. If none has revenue, it uses native directory enumeration order. The [direct order probe](directory-order.json) records the same results for Python and the pinned Bun runtime on the selected filesystem. Complete native comparisons cover populated, empty, single-company fallback, and multiple-company fallback states.

The collector requires physical owner directories and regular Markdown files. Redirects, hardlinks, different file owners, registry aliases, and oversized sources refuse access. Aggregate discovery has a 2,048-entry limit. A source has a 256 KiB limit. Source projection and response transport have a 3 MiB limit.

Native validation and retained-source policy check company labels, report filenames, and Markdown bodies. A private report cannot publish its body or filename. A retired report label cannot return from a current retained file. A retired company label excludes child sources. Unrelated admitted business overview text remains available. The renderer selects the latest report from the admitted reports. It keeps the native response fields and parsers. Its supplied-source form does not reopen files. Default callers retain their filesystem behavior.

The operation rechecks directory entries, selected company state, missing-source state, exact source bytes, file metadata, and current account authority after rendering. Separate processes observe completed rendering before changing report bytes, creating a newer report, or revoking the account. Each change withholds the response.

The [first baseline](baseline.txt) runs eight tests in 9.319 seconds. Eight assertions fail. The populated and empty native comparison cases pass. The [selection baseline](selection-baseline.txt) adds multiple-company fallback and a current company timestamp for the retirement fixture. It runs nine tests in 9.915 seconds and reports eight failed assertions. Complete native comparison cases pass. Exact raw output remains in the [first archive](baseline.raw.txt.gz) and [selection archive](selection-baseline.raw.txt.gz), with separate digest receipts. Readable logs remove trailing ASCII whitespace only.

The [first gate](first-gate.txt) passes nine tests in 13.300 seconds. The [expanded gate](expanded-gate.txt) passes 12 tests in 17.522 seconds with warnings treated as errors. Additional cases cover aggregate discovery limits, retired company labels, Origin, bearer precedence, selectors, and non-GET requests.

The [adjacent gate](adjacent-gate.txt) passes 157 cases in 175.149 seconds without skips and with warnings treated as errors. It covers business, local Work, Finance, Health, Life home and goals, tab metadata, source admission, authenticated response authority, native jobs, the staged daily profile, patch copies, and actual ordered source preparation. The [source identity](source-identity.json) and [dependency selection](dependency-selection.json) record code bytes and unchanged manifests. Both memory patch copies have identical bytes. Ordered preparation applies all 11 Hermes and 23 LifeOS patch groups.

Source-review coverage for the additional classes, remaining readers and writers, user-index publication, and installed ownership acceptance remain open. The business candidate is not deployed to `.252` during this gate.
