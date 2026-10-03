# Native wiki source and cache boundary

Date: 2026-10-01. The listeners use localhost and synthetic files. No running installation changes.

## Reproduction

`probe_wiki.py` starts the real native wiki handler on a disposable Bun HTTP listener. Its process has an approved owner environment. The requests have no request credentials. `before.json` records HTTP 200 responses for the index, unregistered note, current note, search, and graph. After the actual memory service commits a forget operation, the native note handler still returns the retained body. The index and graph retain that note.

This probe starts the exported handler, not the complete PULSE application. Source inspection confirms that `PULSE/pulse.ts` forwards wiki requests after a loopback Host guard. That guard checks the destination hostname, not a memory identity or grant. The probe does not establish internet or LAN reachability of any running installation.

The native process exits cleanly. It emits no stderr. The native routes do not set a `Cache-Control` header in this fixture. The existing frozen PULSE dependency set supplies MiniSearch 7.2.0. No model runs.

## Declared rendering

The native renderer accepts declared page content, metadata, and modification time. It keeps the native frontmatter parser, title extraction, quality, tags, related links, search, excerpts, backlinks, tree, and graph functions. Search, excerpts, and note routes read the declared content, including when a raw file contains a different body. They do not open that file again.

Each rendering operation clears the temporary index before collection and after response creation. An empty later corpus cannot return an earlier note. Duplicate page slugs and source aliases refuse the operation and leave no partial index. Unsupported module routes and write requests refuse rendering.

`renderer-before.txt` records the passing standalone native control and four missing-renderer failures. `renderer-after.txt` records five passing native cases. `renderer-expanded.txt` records nine passing native cases in 0.398 seconds with no skips. The standalone control retains raw native behavior when no managed connector exists.

`renderer-validated.txt` repeats the nine cases with explicit test request validation and passes in 0.363 seconds. Ordered source preparation applies the renderer through the distributed patch. The distributed focused gate passes 51 cases in 33.789 seconds without skips, failures, or errors. It includes nine renderer cases, seventeen canonical cases, twenty staged publication cases, and five preparation and patch-bundle cases. Hermes patch groups remain unchanged. The existing native memory patch now changes 24 files.

## Open integration

The renderer is a collection primitive. It does not authenticate an HTTP request, authorize source selection, or change the current wiki route. The handler leak remains open until the authenticated plugin route supplies a governed corpus and the native listener delegates managed reads to it.

The next integration must include the following behavior:

1. Authenticate the incoming request through the current Hermes owner binding.
2. Select canonical current notes and permitted native retained sources under that binding.
3. Validate declared metadata, paths, text, timestamps, corpus size, and duplicate identities.
4. Render through the native collector in a separate process without raw index startup or watchers.
5. Bind the response to the installation and use `Cache-Control: no-store`.
6. Test current notes, unregistered notes, correction, forget, connector failure, and access revocation through the live route.
7. Trace public system documentation and the separate skills, hooks, worker, reindex, and edit routes.

The standalone renderer control is necessary but does not establish complete wiki parity. Native MemoryGraph caches and the Observability knowledge routes remain separate open readers.
