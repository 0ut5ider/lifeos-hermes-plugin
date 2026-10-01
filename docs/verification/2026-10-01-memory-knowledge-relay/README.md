# Authenticated Observability Knowledge reads

Date: 2026-10-01. This unit governs the native Observability Knowledge index and note read routes. It uses actual Hermes authentication and isolated native rendering against prepared public source trees. All user data is synthetic and disposable.

## Verification

- [Before cases](before.txt): seven of eight live cases fail. The native standalone control passes. Raw reads, correction history, anonymous writes, revocation, cross-origin reads, and graph-cache access reproduce the measured gaps.
- [First corrected cases](after-first.txt): all eight live cases pass in 12.640 seconds.
- [Renderer and transport probes](render-and-http.txt): the paired native control exposes nondeterministic ordering for notes with equal update dates. A transport fixture uses the wrong header mutation and fails to change the installation binding. The oversized-response control also records an expected peer reset from early refusal.
- [Corrected renderer and transport cases](render-and-http-after.txt): 21 cases pass in 6.806 seconds. The paired comparison sorts notes with equal update dates by slug. The transport fixture changes the actual response header.
- [Distributed focused gate](focused.txt): 139 cases pass in 129.944 seconds without skips, errors, or failures. The gate includes native renderer and HTTP cases, existing wiki and retained-source cases, current canonical reads, authentication, source preparation, and both bundled patch copies.
- [Completion marker](focused.done): exit status 0. The [runner](run_gate.py) records exact commands and source paths.
- [Ordered preparation](preparation.txt): a new source tree receives every bundled patch. Hermes uses base `758ad514eb0e800547e015edf05aa18f78b78d82`; LifeOS uses base `5e2f2e8c0abde612da0e99c16c0d07d4ec21b88c`.

The test HTTP server captures peer resets only for an intentionally oversized response. Cleanup asserts the cause and error type. Unexpected resets still fail the fixture. The final focused output is clean.

## Native behavior

The managed index retains native domain counts, quality bands, note metadata, and tags. The managed note route retains native response fields and uses only the current registered projection. Corrected and forgotten native history remains on disk but cannot re-enter these read routes. A later empty request cannot retain an earlier source map. Missing declared files do not trigger raw stat or read operations.

The native standalone control preserves raw index, note, and PUT behavior when no managed connector or marker exists. The existing native memory patch adds Observability as its 25th file. Both patch copies are identical and have 105,370 bytes. No Hermes patch group is added. The bundle remains nine Hermes and ten LifeOS patch groups.

## Remaining work

Managed note PUT returns 405 because it does not have reviewed current references. A complete edit transaction must bind the observed note and references, reject stale or private edits, retire replaced facts, retain history, and publish the note and derived indexes together. Blocking an unsafe native write does not establish editing parity.

Managed `lastHarvest` remains null. The raw `_index.md` cannot establish current managed harvest metadata. The direct raw graph cache returns 404 until governed graph publication exists. Other Observability source routes remain outside this unit.

The actual mount renderer, sidecar editing and backup readers, derived publication, complete reader inventory, restricted delivery, lifecycle, recoverable ownership setup, and full release review remain open. This unit does not activate ownership, deploy, push, or modify `.211`, `.212`, or `.213`.
