# Staged daily Pulse configuration

Date: 2026-10-08. The [profile](../../deployment/daily-text/PULSE.user.toml) uses the prepared morning-brief candidate.

The profile disables voice, the GitHub Work module, Cloudflare Synapse, and Claude subscription usage. The native module merger preserves the required Life and memory surfaces. The profile does not change the private model tiers.

The job merger retains nine jobs, with five enabled jobs and no duplicate names. Consolidation, proposal cleanup, and the morning brief call the fixed Hermes owner command. They have a 600-second Pulse timeout around the command's 540-second limit. The healthcheck uses local log output. Cost aggregation retains its shipped configuration. The four unavailable Assistant subsystem jobs remain disabled.

The [baseline](baseline.txt) records six failures because the staged profile is absent. The [first gate](first-gate.txt) passes those six cases. The [final gate](final-gate.txt) passes eight cases in 11.113 seconds with warnings treated as errors. Tests load the profile through native `loadConfig` and `resolveModules`. Native `spawnScript` launches the actual Hermes command parser. These processes publish a private weekly synthesis, render a synthetic morning goal, and run proposal cleanup. Disabled ownership and a removed local account refuse consolidation. An inherited Discord author cannot replace the local grant. The native healthcheck returns `NO_ACTION` with no configured sites.

The launcher in each disposable fixture starts the actual Python Hermes entry point. Tests do not replace a native program or model request. The synthetic runs make no model request. Existing owner-job tests cover native process lifetime and repeat publication.

A separate read-only probe rules out the proposed home-directory mismatch. Bun reports the supplied synthetic HOME through `node:os.homedir()`. The installed Pulse service also selects the fresh-store home and working directory. No path correction is necessary.

All job output remains local in this staged file. Morning Discord delivery requires the pending verified private channel and current delivery permission. The native notification helpers read the system file separately, so this profile contains no ineffective notification-section overrides. Final deployment must leave excluded transport credentials unset and test actual notification behavior.

This gate verifies configuration resolution and native job spawning. It does not verify daemon scheduling, restart, live private model requests, installed memory activation, or Discord delivery. The profile has not been installed on `.252` or a daily server.
