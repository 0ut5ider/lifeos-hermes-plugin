# Native wiki request admission

Date: 2026-10-01. Tests use disposable native profiles and two real localhost listeners. No model runs.

The wiki renderer already accepts declared text. The HTTP handler still returns native responses to anonymous requests. The baseline test finds six missing authentication checks. Managed startup must avoid the raw index, watchers, and safety timer. The handler must use incoming credentials through the fixed authenticated Hermes route on every read.

The first integration passes correction, forget, revocation, connector loss, and dashboard shutdown cases. A further probe returns 200 for a cross-origin request with owner cookies. The memory snapshot handler already checks the origin. The wiki handler needs the same check. The corrected route returns 403 before it delegates credentials.

The wiki and Cortex assign categories differently. The native wiki uses the Knowledge directory. Cortex reads the frontmatter `type` field. A Research note with `type: idea` must remain a Research wiki page. The first test changes the header length and receives 503 because the recorded body position no longer matches. That does not prove the category defect. An equal-width header mutation preserves the registered body and produces the expected wrong-route 404. The plugin now uses the native directory mapping.

The focused gate initially passes 84 cases. The category case adds one test to the final gate. The archive keeps both category probes, including the inconclusive first probe. The source paths, commands, full output, and completion markers are in [the verification directory](../docs/verification/2026-10-01-memory-wiki-relay/README.md).

This unit admits registered current Knowledge notes. It does not admit retained silos or documentation by silently scanning them. Their complete source inventory and governed collection remain open. Managed editing, skills, hooks, Arbol, and reindex routes return a refusal until their read or write boundaries are implemented.
