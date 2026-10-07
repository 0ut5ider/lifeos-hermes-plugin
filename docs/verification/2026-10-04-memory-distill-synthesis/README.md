# KnowledgeDistill headless synthesis

Date: 2026-10-04. This gate runs the native distill command, native inference, the shipped child launcher, and actual local HTTP requests. All source content and model responses are synthetic. It makes no server changes.

The [baseline](before-output.txt) fails four controls. The original command exposes an unregistered private note to the model request, publishes after source edits and revocation, and creates a digest with public read permissions. The [baseline source](baseline-test-source.py) retains the tested version.

Managed synthesis prepares current admitted notes and native configuration through the memory service. The native command keeps its parser, ranking, caps, deduplication, and digest templates. It checks source and destination signatures before and after inference. It validates generated fields, private content, retired claims, and cited source paths before effects. External content routing requires a separate reviewed integration.

The service journals digest and tracking state publication as one recoverable operation. Both files have mode 0600. Source edits, authority changes, and later destination edits prevent publication. An actual process exit 73 between file writes restores both previous files on the next governed read.

The [schema probe](schema-before-output.txt) fails when a malformed lane contains an object. The corrected boundary checks the lane type before set membership. The [consistency gate](consistency-output.txt) passes ten cases. The [final gate](final-output.txt) passes 218 tests and 104 subtests in 332.51 seconds without skips. It includes the prior distill marking format correction and all twelve synthesis controls.

The [native recorder](controls-output.txt) captures twelve passing [controls](native-outcomes/). It retains actual process output, synthetic source and artifact bytes, HTTP requests, and local notification requests. The selected original-native health branch matches complete digest bytes, state bytes, and command output. The second synthesis run reports no fresh candidates and sends no additional model request. Native notification retains voice_enabled=false.

The [source comparison](source-comparison.json) verifies all 48 distributed files against the candidate source. Both patch copies are byte-identical. All 80 [final source hashes](final-source-check.json) match. The [prepared manifest](final-source-manifest.json) identifies the tested fixture. Dependencies come from the preceding prepared fixture. This gate does not claim a fresh dependency installation or TypeScript type checking.

These controls establish selected native synthesis behavior with a scripted local model response. Live private FlashNext generation, other active publishers, aggregate ownership recovery, import, Hermes management, background jobs, voice, and the combined release remain open. Ownership and sharing stay disabled on running installations.
