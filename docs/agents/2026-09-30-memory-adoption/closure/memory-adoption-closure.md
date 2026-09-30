# Native source adoption closure review

Date: 2026-09-30
Role: Independent code reviewer
Question: Do the three adoption fixes close the confirmed defects, and does the new owner preferences/API/UI integration preserve scope, preview identity, retries, and truthful outcomes?
Model: GPT-6. The exact model variant is not exposed in this agent context.

## Conclusion

All three findings from the initial review are closed in the reviewed snapshot. The four original fixture cases now produce safe results, without changing the probe. All 38 focused tests passed. An additional SDK probe verified pagination, identical retries after a lost response, and committed-result reporting after status refresh failure. No new material defect was found in this bounded closure review.

This is closure of the adoption unit and its owner preferences/API/UI surface. It is not approval to activate memory ownership or a complete release audit.

## Verified fixes

| Initial finding | Current implementation | Independent result |
|---|---|---|
| Body text matched YAML title, creating an unreadable reference | _body_source derives the body start from the same frontmatter delimiter shape as native discovery | Adoption commits the body occurrence and ordinary recall returns it without conflict |
| Trimmed trailing spaces created an unreadable reference | Body and section construction preserve non-newline whitespace | Recall returns the adopted content with all three trailing spaces intact |
| File mtime could change eligibility without invalidating preview | Signature includes mtime_ns and canonical candidate, pending, and excluded collections | Original signature returns conflict after touching the excluded learning note; recall remains empty |
| Hot-memory adoption could restore a wrapped exact forgotten quote | Retained history/quote filtering runs for every adopted fact category | Hot rule is excluded; adoption commits zero facts and recall remains empty |

The last two rows correspond to separate initial findings. The first two rows are the two independently reproduced variants of the reference-integrity finding. Raw unchanged probe output is in raw/original-probes.txt. The exact original probe was also copied into raw/probe_adoption.py.

The quote defense remains based on normalized retained claims. No universal semantic paraphrase guarantee is asserted.

## Owner preferences and HTTP boundary

MemoryPreferences constructs its owner scope from the validated installed configuration. Neither preview nor adoption accepts a caller-provided scope, principal, or root. The preview route requires an empty dictionary. The adoption route requires exactly signature, projects, and request_id. Extra envelope fields return HTTP 400. The underlying adoption operation validates signature shape, project mapping, project eligibility, and the bounded request identifier.

The preferences test exercised project assignment, owner recall of the adopted result, and unchanged disabled ownership. The real FastAPI test previewed a native note and committed its adoption through HTTP. Spoofed caller/root fields and extra dry_run data were rejected. Existing preferences root checks, concurrent sharing root checks, sharing disable behavior, strict fact review, and proposal controls continued to pass.

The synthetic ASGI tests mount the plugin router directly. They exercise actual FastAPI parsing and actual native storage, but do not repeat the Hermes dashboard authentication middleware check. These routes inherit the existing authenticated dashboard mount; no new standalone server is introduced by this unit. Authentication runtime and activation remain outside this closure scope.

## UI outcomes and retries

Code inspection and the SDK tests confirm that the panel:

- Displays source text, path, historical learning labels, unknown author labels, pending proposals, and exclusion reasons.
- Leaves project assignments blank by default and explains that assignment permits readers of that project to read the note.
- Sends the exact preview signature and path-to-project mapping.
- Retains a conflicted preview and its reason.
- Reuses the request identifier when retrying an unchanged adoption payload.
- Generates a new request identifier after a project assignment changes or a fresh preview arrives.
- Does not treat adopted pending proposals as accepted changes.
- Offers no ownership activation control.

The additional probe rendered 26 records. Page one contained records 0 through 24 and page two contained record 25. A project assignment on page one survived pagination. After a simulated lost response, the retry request was byte-equivalent in its structured payload, including request_id. The project name was trimmed to lab, and all other sources remained unassigned.

The successful retry returned a committed result, then the status refresh failed. The panel removed the completed preview and retained this truthful message:

Added 26 fact(s) and 0 pending change(s). Native files remain unchanged. Could not refresh memory status: Synthetic status refresh failure

That probe is raw/probe_ui.cjs, with output in raw/ui-probe.txt. This is a component-level SDK simulation, not a browser or transport end-to-end test. Actual HTTP/native adoption and backend idempotence are verified separately by the Python fixtures.

## Test results

| Suite | Result | Output |
|---|---|---|
| test_memory_adoption.py | 16 passed | raw/adoption.txt |
| test_memory_preferences.py | 8 passed | raw/preferences.txt |
| test_memory_dashboard.py | 3 passed | raw/dashboard.txt |
| test_memory_dashboard_ui.cjs plus test_dashboard_ui.cjs | 11 passed | raw/ui.txt |
| Original four adoption probes | All expected safe outcomes | raw/original-probes.txt |
| Pagination/retry/refresh SDK probe | Passed | raw/ui-probe.txt |

Total focused tests: 38 passed, zero failures, zero skips. The adoption suite includes the 501-learning-source case, strict unknown-project visibility, appended section correction, native proposal adoption, and real child interruption during learning-to-Research correction.

Python environment: /home/outsider/.cache/lifeos-plugin-memory/memory-plugin-test-env/bin/python.

Native source: /home/outsider/.cache/lifeos-plugin-memory/source-gate-20260930-adoption/lifeos/LifeOS/install.

Prepared host source for dashboard imports: /home/outsider/.cache/lifeos-plugin-memory/source-gate-20260930-adoption/hermes. This is owned prepared source, not a live runtime.

## Evidence and boundaries

raw/commands.txt records test and probe commands plus both source environment variables. Initial and final hashes, source snapshots, the native retriever hash/snapshot, and patch equality results are saved in raw/. The reviewed sources did not change during this closure. Top-level and bundled LifeOS memory patches are byte-identical.

No implementation files were edited and no commits were made. All native records and configuration used by tests were disposable synthetic fixtures. No live services, SSH, actual accounts, credentials, actual memory records, or journal tools were accessed.

No full browser runtime, activation, broad lifecycle, install/restore, or complete release gate was run. Existing broader open gates remain open. This review supports a development checkpoint for the bounded adoption unit.
