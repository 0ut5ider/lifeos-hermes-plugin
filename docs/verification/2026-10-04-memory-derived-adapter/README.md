# DerivedSync PULSE child acceptance

Date: 2026-10-04. The native synchronization command starts actual adapter children in a synthetic install. Model calls use the shipped shim and memory runtime with a scripted local HTTP server.

The [baseline](before-output.txt) has four failures. The managed dependency guard refuses every plan that contains an adapter. The preceding adapter source, publication, and inference controls establish the required dependency, so the temporary guard is removed. Source and authority rechecks remain active before each child and before tracking publication.

The [candidate](candidate-output.txt) passes four controls. Actual generation publishes the native page and tracking files. A cached child preserves page bytes and sends no model request. A missing-source child retains the native successful skip. Revocation during a model request refuses both page and tracking publication and releases the synchronization lock.

The [final gate](final-output.txt) passes 154 tests and 102 subtests in 185.84 seconds. It adds an original-native parent comparison for cached-child effects. Current source hashes, changed paths, command, exit status, page bytes, index entries, and quiet subsequent behavior match. Clock values and durations are excluded from equality. The adapter child remains governed in both parent controls. The comparison does not establish all standalone adapter branches.

The [recorder](controls-output.txt) retains five passing [native controls](native-outcomes/), including actual process output, file contents, permissions, and HTTP requests. All final [source hashes](final-command.json) match. The native distribution and both memory patches remain unchanged. No server changes occur. The local server supplies scripted content, so private FlashNext generation quality and live provider availability remain separate requirements.

This closes the temporary DerivedSync adapter refusal for the tested distribution. Complete adapter output transactions, other native publishers, service recovery, ownership activation, import, management, background jobs, routing, voice, and the combined release remain open.
