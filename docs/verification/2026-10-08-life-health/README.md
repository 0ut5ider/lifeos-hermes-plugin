# Native Life health admission

Date: 2026-10-08. The source tree uses the prepared health-view candidate.

Managed `/api/life/health` uses the fixed authenticated Life relay. The route requires current owner recall and refuses anonymous requests, revoked account bindings, foreign Origin, non-GET requests, and source selectors. Connector loss leaves the managed route closed.

The owner operation checks the selected physical health directory before discovery. It admits current markdown contents and dynamic filenames through native text validation and retained-source policy. Markdown bodies, headings, and filenames disappear when private or retired source text excludes the record. Lab reports contribute filenames and file metadata only. The operation does not read or classify PDF contents.

The collector refuses redirects, hardlinks, a different file owner, an alias of the memory registry, and oversized markdown. Discovery has a 2,048-entry limit. Individual text sources have a 256 KiB limit. The source transport and complete response have a 3 MiB limit. The final operation rechecks content, selected metadata, directory entries, and current account authority after rendering.

The native renderer retains the existing health sections, file labels, lab-report list, and freshness fields. Its supplied-source form cannot reopen a file. Default callers keep the existing file reader. Tests compare the complete native response for populated, empty, and repeated-dot filenames.

The [first baseline](baseline.txt) has six failures across eight cases. Its retirement marker appears only in a heading that the native parser discards. That negative assertion passes without proving retirement. The corrected fixture puts the marker in a rendered body and verifies delivery before forgetting. The [corrected baseline](retirement-baseline.txt) has seven failures and one native comparison pass.

The [first gate](first-gate.txt) passes eight cases. The [expanded gate](expanded-gate.txt) passes 13 cases. A further [filename baseline](filename-baseline.txt) finds an incorrect restriction in the candidate. The [direct native probe](filename-probe.jsonl) confirms that repeated dots in a leaf filename trigger the candidate's path check. The correction rejects actual path components while preserving that valid filename. The [final gate](final-gate.txt) passes 14 cases in 19.447 seconds with warnings treated as errors.

Separate processes observe actual completed native rendering before changing markdown, adding a lab filename, or removing the owner binding. Each change withholds the result. Other cases cover source limits, private source names, retained forgotten notes, retained retired lab filenames, redirects, hardlinks, connector loss, and exact native field comparisons.

The [adjacent gate](adjacent-gate.txt) passes 119 cases in 121.491 seconds with no skips and warnings treated as errors. It includes the Life views, tab metadata, native morning brief, staged daily profile, authenticated response checks, source admission, patch copies, and actual ordered source preparation.

The [source identity](source-identity.json) records the final product, native, patch, and test hashes. The [dependency selection](dependency-selection-final.json) reuses accepted dependencies after exact manifest and lock comparison. Preparation applies all 11 Hermes and 23 LifeOS patch groups. Both memory patch copies have identical bytes.

Installed ownership, live Discord acceptance, remaining Life routes, and user-index publication remain open. The health candidate is not deployed to `.252` during this gate.
