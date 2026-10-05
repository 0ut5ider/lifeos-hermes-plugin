# Native inference verification log

Date: 2026-10-04. The gate runs actual native adapter inference through the shipped child launcher and a local HTTP model fixture. The model response and all content are synthetic. It makes no server changes.

The [baseline](before-output.txt) fails both controls. Native inference creates a verification log with mode 0644. It also appends through a symbolic link to a foreign file. The [baseline source](baseline-test-source.py) retains these regressions. The [engineering note](../../../notes/2026-10-04-inference-verification-log.md) records the finding.

Managed inference sends its native metadata to the memory service. The fixed verification destination uses the existing private journaled publisher. The service admits bounded native fields, checks current unrestricted owner authority, and validates decoded content against current policy. It refuses redirected or hard-linked destinations and preserves later destination edits. The native command retains best-effort logging. A refused log does not change the model result.

The [candidate gate](candidate-output.txt) passes 29 tests and three subtests in 114.40 seconds. It includes native adapter inference, headless synthesis, adapter collection, and the two real logging regressions. The [publication gate](publication-output.txt) passes seven tests and four subtests in 1.47 seconds. It verifies exact native metadata bytes, private permissions, malformed and private metadata, restricted authority, later edits, revocation, and actual process exit 73 after append. The next governed transaction restores the previous log.

The [recorder](controls-output.txt) retains nine [passing controls](native-outcomes/), actual native process output, HTTP requests, and synthetic artifact bytes. The [source comparison](source-comparison.json) verifies all 49 distributed native files against the candidate. Both patch copies match. The [manifest](prepared-source-manifest.json) identifies the tested fixture. [Final hashes](final-source-hashes.json) identify the bridge and tests. Dependencies come from the preceding prepared fixture. These results do not claim a fresh dependency installation or TypeScript type checking.

The selected logging path is governed. Live FlashNext acceptance, remaining native routes, aggregate ownership recovery, import, Hermes management, jobs, voice, and the combined release remain open. Ownership and sharing stay disabled on running installations.
