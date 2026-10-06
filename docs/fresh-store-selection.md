# Fresh store selection and return

Date: 2026-10-05. Status: proposal for Adrian's review. No code implements selection yet.

A prepared fresh store is a complete LifeOS installation at `<state>/fresh-stores/<profile>/<identifier>/home/.claude`, with its user data at `home/.config/LIFEOS/USER`. Selection makes that installation the active LifeOS for one Hermes profile. Return makes the previous installation active again.

## Current layout on `.212`

- `~/.claude` is a link to `~/.hermes`. LifeOS files (`hooks`, `LIFEOS`, `settings.json`, `skills`) and Hermes files share that directory.
- LifeOS user data is in `~/.config/LIFEOS/USER`.
- The plugin reads hook registrations from `~/.claude/settings.json` and uses `~/.claude` as the installed root.
- `Mount.ts` writes LifeOS identity and guard files into the Hermes profile.
- The Pulse user service runs from the installed tree.
- The profile has no `lifeos-memory.json`, so lasting-memory ownership is not configured.

## What selection must change

1. The installed root that the plugin, the hooks, and Pulse use.
2. The mounted Hermes files from `Mount.ts`, rendered from the fresh tree with the Adrian and Cerebo identity.
3. The VersionDrift baseline, created for the fresh tree.
4. The services: gateway, dashboard, and Pulse restart against the fresh tree.

Selection does not change lasting-memory ownership. That stays a separate activation with its own gates.

## Recommended design

Point the plugin at the selected installation through one profile setting, not through the `~/.claude` link.

1. Add `lifeos-installation.json` to the Hermes profile. It names the selected installed root and user data path. Without the file, the plugin keeps today's `~/.claude` behavior.
2. Selection is a journaled transaction, like the ownership transaction:
   1. Require a `review` store, the owner, and a free installation lock.
   2. Create a verified profile backup.
   3. Stop the gateway, dashboard, and Pulse.
   4. Publish `lifeos-installation.json`, run `Mount.ts` from the fresh tree, create the VersionDrift baseline, and point the Pulse unit at the fresh tree.
   5. Start the services and verify a model turn and the hook registration.
   6. On any failure, restore the backed-up profile files and the previous setting, and restart the services.
3. Return is the same transaction in reverse. It restores the recorded previous installed root and the backed-up mounted files. It keeps the fresh store on disk.
4. The retained installation in `~/.hermes` is never moved or deleted.

## Why not swap the `~/.claude` link

- On `.212` the link target holds Hermes files too, so the old and new trees cannot be separated by one link.
- Claude Code and other tools on the same account also follow `~/.claude`.
- A link swap gives no record of what to restore, and an interrupted swap leaves no recovery state.

## Cost and risk

- Files: the plugin installed-root lookup (`dashboard/plugin_api.py`, `bridge.py`, `memory_preferences.py`), a new selection transaction module, the Pulse unit writer, routes, and page controls.
- Risk: every component that assumes `~/.claude` must use the setting. A missed reader keeps using the old tree. A search for `.claude` readers and a paired run on the selected tree are required.
- Tests: transaction and recovery tests on fixtures, then a service-backed selection and return in the disposable LXC before `.212`.

## Decision needed

Approve the profile setting design, or choose the link swap.
