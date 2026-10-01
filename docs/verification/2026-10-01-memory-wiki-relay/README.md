# Authenticated native wiki reads

Date: 2026-10-01. The tests use disposable native data, a Bun wiki HTTP listener, and the actual Hermes dashboard authentication middleware on a separate Uvicorn HTTP listener. No model runs. No running installation changes.

## Behavior

Managed wiki startup does not build the raw file index or start its watchers and safety timer. Each incoming read delegates its bearer token or supported Hermes session cookies to the fixed local dashboard endpoint. Ambient owner variables and the internal worker flag do not admit an HTTP caller.

The dashboard verifies the actual Hermes session and its current installation owner binding. It selects registered current Knowledge notes under one cooperating memory transaction. The native renderer retains page parsing, directory categories, search, excerpts, note bodies, backlinks, and graph output. The worker uses declared text and clears its temporary index after each result.

The six admitted route forms are:

- `/api/wiki`
- `/api/wiki/graph`
- `/api/wiki/search?q=QUERY&limit=COUNT`
- `/api/wiki/backlinks/SLUG`
- `/api/wiki/doc/SLUG`
- `/api/wiki/knowledge/DOMAIN/SLUG`

The relay accepts one validated route descriptor. It cannot select another server or dashboard API. Only search accepts query parameters. The result count is between 1 and 200. The search query limit is 1,024 characters. The declared source and response limits are 3 MiB. The existing relay timeout is 8 seconds. Native workers retain their 30-second limit.

Every response disables storage with `Cache-Control: no-store`. Native missing pages retain status 404 and require the matching installation binding. Managed editing returns 405. Reindex, skills, hooks, Arbol, and unknown wiki routes remain unavailable. Cross-origin requests return 403 before credential delegation. Missing or invalid connectors and unavailable dashboards return 503 without a raw fallback.

## Evidence

- [Authentication baseline](auth-before.txt): six missing authentication checks fail against the prior distributed source.
- [Cross-origin baseline](origin-before.txt): the first integration incorrectly returns 200 with authenticated cookies.
- [Initial category probe](category-before.txt): changing header length returns 503 because the registered body position changes. This probe does not establish category behavior.
- [Equal-width category probe](category-equal-width-before.txt): the registered body remains valid, but the Research wiki route returns 404 when the plugin uses the frontmatter type.
- [Distributed focused gate](focused.txt): 85 cases pass in 80.248 seconds. There are no skips, failures, or errors. The gate includes 15 live wiki cases, native standalone renderer controls, existing relay and authentication cases, current canonical reads, and actual ordered source preparation.
- [Completion marker](focused.done): exit status 0.
- [Gate runner](run_gate.py): exact source paths and commands. It also supports the complete memory regression and neighboring Hermes provider and patch contracts.

Prepared sources use Hermes base `758ad514eb0e800547e015edf05aa18f78b78d82` and LifeOS base `5e2f2e8c0abde612da0e99c16c0d07d4ec21b88c`. Both memory patch copies are identical. This unit changes two existing native patch paths and adds no Hermes patch group.

## Limits and next work

This unit covers registered current Knowledge notes in the six native archive directories. It does not claim that the complete native wiki corpus is admitted. Retained WORK, LEARNING, WISDOM, and RESEARCH sources, installed documentation, generated system prompts, and their source projections remain open. Unknown notes do not enter the managed wiki automatically.

The tests exercise real HTTP handlers and authentication. They do not exercise the complete PULSE browser interface, LAN Secure cookies, proxy deployment paths, or scheduled model delivery. Copied stateless bearer tokens retain the existing host semantics after browser logout. Removing the owner account binding revokes the next request.

The remaining native reader inventory, Observability routes, sidecar editors, graph caches, derived publication, restricted delivery, lifecycle, recoverable ownership setup, and full release review remain open. Memory ownership remains disabled on running installations.
