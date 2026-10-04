# Catalog callback release on .212

Date: 2026-10-04. Both active test installations on `192.168.8.212` now run tested plugin revision `02d7ac85d96fb416b3c8832928d274ec9ddab4cf`. The plugin still declares version `0.1.0`. This update replaces the previous merged revision `d5dafbc` and preserves the existing profiles and user data.

The code change makes Hermes catalog search results pass through the existing result transform and augmentation callbacks. Native LifeOS Safety now examines the search result and returns its complete warning to the caller. The installed pre-fix control performs a real search but never invokes Safety.

## Installed change and verification

| Check | Discord profile | Browser acceptance profile |
| --- | --- | --- |
| Account | `lifeos-hermes` | `lifeos-plugin-install-probe` |
| Plugin revision | `02d7ac8` | `02d7ac8` |
| Package files matching the pinned revision | 75 | 75 |
| Changed runtime files | `model_tools.py` and the bundled Hermes events patch | Same two files |
| Dependency changes | None | None |
| Native source or hook setting changes | None | None |
| Services | Gateway, dashboard, and Pulse active | Gateway, dashboard, native dashboard, and Pulse active |
| Actual plugin manager | Nine hooks and both required middleware callbacks load | Same result |
| Installed native Safety control | One invocation, exit 0, complete warning delivered | Same result |
| Real model and terminal turn | `pwd` succeeds; expected final reply arrives | Same result |
| Dashboard HTTP checks | `/chat` and `/lifeos-bridge` return 200; unauthenticated `/api/plugins` returns 401 | Same result |
| Private recorder | 431 turn events; 24 hook starts and 24 completions; no reported capture gaps | Same result |
| Recorder source validation | Nine source fingerprints match; gateway and dashboard initialize with the new pin | Same result |
| User data at code replacement | All selected native USER, MEMORY, and Hermes memory file hashes remain unchanged | Same result |
| Protected profile files | Configuration, credentials, identity, memory configuration, and hook settings remain unchanged | Same result |

[release-results.json](release-results.json) contains the measured results. [regression.log](regression.log) records 24 passing source, callback, preparation, footprint, and evidence cases. [regression-command.json](regression-command.json) records the command and synthetic fixture paths. The earlier [full candidate gate](../2026-10-03-hook-compatibility/README.md) remains separate evidence: 1,047 passing cases and 20 skips. This deployment does not repeat that full gate.

The Discord Hermes checkout retains local base commit `6056259` with the catalog callback overlay. The acceptance checkout retains its existing patched source and helpers. Both installed `model_tools.py` files have SHA-256 `ca07054ca98d5bd2b28b9e45d2efacddea5e583330f4daa8efd4d327c31734dc`. The update does not reset either checkout or push a Git branch.

## Deployment and rollback

[deploy_catalog.py](deploy_catalog.py) checks the exact before and after code hashes, all package files, profile hashes, and recorder fingerprints. It takes a private snapshot and records intent before stopping services. It copies only the two changed runtime files, updates the plugin and recorder revision metadata, then restarts and verifies services. A failed verifier restores the prior code and revision metadata and restarts the services.

The first Discord apply automatically rolls back because the verifier requires surrounding warning whitespace to remain byte-identical. Inspection shows that Hermes returns all 163 bytes of the stripped warning. Existing augmentation trims the native warning's surrounding blank lines. The corrected [catalog verifier](verify_catalog.py) checks the complete stripped text, one native invocation, and a successful native exit. Both repeated applies pass.

The initial model-turn launcher probe refers to an absent profile-local command. The corrected [tool probe](smoke_tool.py) uses the same checkout-local launcher as the service. An initial HTTP probe also uses loopback for a dashboard that binds the LAN address. Neither probe changes production configuration. The final checks use the installed launcher and bound address.

[rollback-rehearsal.json](rollback-rehearsal.json) records an actual filesystem exercise. Atomic copy and restore work, later user data and unrelated metadata survive, and a changed later code file refuses restoration. [final_verify.py](final_verify.py) checks active services, runtime registration, actual model tool output, recorder process metadata, and capture completeness.

Private release directories retain code snapshots, configuration snapshots, control fixtures, failed controls, and model streams. They are owned by each account and have mode `0700`. Raw profile content and recorder artifacts stay on `.212`.

An operator can restore the prior code with these commands. Restore preserves current user data and refuses a later code change. It restarts the selected profile's services.

```sh
sudo -u lifeos-hermes python3 /home/lifeos-hermes/workspace/releases/20261004-catalog-02d7ac8/deploy_catalog.py discord restore
sudo -u lifeos-plugin-install-probe python3 /home/lifeos-plugin-install-probe/acceptance-20261002/workspace/releases/20261004-catalog-02d7ac8/deploy_catalog.py acceptance restore
```

## Practical availability

The Discord entry point remains `#hermes-212`. The [Hermes dashboard](http://192.168.8.212:9119/chat) serves that profile. Normal chat, installed tools, LifeOS skills, mounted context, session history, Hermes built-in memory, and the private development recorder remain available.

| Limitation | Practical effect |
| --- | --- |
| LifeOS memory ownership remains disabled | The Discord profile uses Hermes built-in memory. It does not use the new LifeOS provider as the single owner of facts and preferences. Governed LifeOS recall, corrections, and forgetting are not active as a complete system. |
| Existing-memory import is unimplemented | The profile does not acquire existing facts, preferences, or history from `.211`, `.213`, or another agent. It retains the fixture's `Test Operator` identity and fresh personal tree. |
| Optional memory sharing is not enabled | Other agents do not share this profile's native memory through the new Model Context Protocol service. |
| LifeOS Pulse jobs remain disabled | The Discord profile does not run cost aggregation, periodic health checks, memory consolidation, proposal cleanup, or the morning brief. Hermes scheduling is a separate available feature. |
| Complete installation and update from Hermes is deferred | An operator still needs to install and maintain the full compatibility set. Existing dashboard update and restore controls do not supply the complete Hermes-managed workflow. |
| Optional external and desktop integrations are unconfigured | Voice, Cloudflare, and GitHub login are unavailable in this fixture. Claude subscription quota reporting has no native OAuth credentials. Kitty terminal effects do not apply to Discord. |
| Four model tiers route to one private model | Haiku, Sonnet, Opus, and Fable select effort settings for `flashnext-w4a16-fp8ple`. Their labels do not provide four different model weights. |
| Remote project access requires its own setup | SSH and Docker hooks need configured targets and workspace trust. Temporary acceptance credentials, containers, and Docker access were removed after testing. |

## Remaining verification limits

Hook registration and dispatch do not establish every native effect. The ledger has paired dispatch evidence for 65 of 74 registrations and selected effect cases for eight registrations. Nine native controls and additional handler branches remain open. These evidence gaps do not mean that Hermes web tools are disabled.

The update does not enable memory ownership, sharing, scheduled Pulse jobs, or a new messaging destination. It does not send a new Discord test message. The real tool checks use CLI turns. Complete memory activation, full hook parity, and the Hermes-managed installer remain open. The `.211` and `.213` installations remain unchanged.
