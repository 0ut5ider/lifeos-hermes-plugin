2026-10-15
Role: Independent focused closure reviewer
Question: Does the reviewed local-owner route enrollment close fresh-claim admission without weakening identity, destination, route, or recovery controls?
Model: gpt-6.1-sol, high reasoning effort

# Owner route closure

Reviewed commit: `e5e1a75d8a892b08dad724a3640a97f619405f26`. Base: `f63a644d`.

**The prior missing-identity finding is closed within the tested component, resolver, and actual service boundaries. No new finding is identified. All 53 controls pass.**

## Finding disposition

The prior dashboard claim creates only the dashboard owner binding. Its activation enables the provider without an admitted conversation account or destination. The correction now prepares a local operating-system account binding, the exact selected profile destination, and the actual selected Hermes model route. The ownership target digest binds those grants before the separate owner application.

The correction refuses a conflicting local principal and an existing restricted local destination. It preserves unrelated grants and existing local permissions. It adds only the current route to an existing unrestricted local owner grant. A changed model configuration invalidates the old review before ownership publication.

The ready review discloses the account, destination, model, resolved provider, and route hash. The actual manager component displays these values before application. Its component test verifies that displaying the review does not send an application request.

The resolver starts an isolated Python child with the fixed profile selected through `HERMES_HOME`. It checks the configuration byte hash before and after Hermes resolution. The parent receives bounded route fields, not the credential. Failure messages are generic. Resolution loads selected-profile dotenv values only in the child.

## Independent verification

| Run | Result | Boundary |
| --- | --- | --- |
| `review-owner-route-existing` | 43 PASS | Owner access, activation, ownership, setup, and repeated lifecycle controls |
| `review-owner-route-independent` | 6 PASS | Actual route resolution, admission denial, profile selection, dotenv, named provider, changed config, and private error fields |
| `review-owner-route-isolation` | 1 PASS | Actual synthetic parent Python startup payloads do not execute in the isolated child |
| `node --test tests/test_memory_removal_ui.cjs` | 3 PASS | The actual manager component with its SDK test implementation |

The independent route controls verify the actual resolved route hash. That hash admits the local owner. An unknown author, another profile destination, and an unapproved route remain denied. A poisoned parent `HERMES_HOME` does not select another profile's model. Parent Python path and startup inputs do not execute a synthetic `sitecustomize.py` payload in the child.

A selected-profile dotenv endpoint resolves correctly. The synthetic credential does not appear in returned route or disclosure objects, and child dotenv variables do not enter the parent environment. A named custom provider resolves its configured endpoint without returning its credential. An edit made immediately before child startup causes refusal and keeps the later configuration bytes. A credential-bearing invalid endpoint produces a generic error without its synthetic credential or hostname.

The 43 existing controls include later policy and model edits, wrong-owner refusals, actual service writer restarts, retained later native facts and forget decisions, real process exits during configuration publication and recovery, and a repeated activation after verified return. They use the shared systemd fixture lock and its owned-unit cleanup.

## Original regression preservation

`original-finding/` retains the original failing control and raw output. That historical control deliberately uses `model_route='synthetic-reviewed-route'`. This constant is not a reviewed route. The closure does not count the historical control as passing or weaken route admission to make it pass. Closure uses the actual resolved and reviewed route instead.

## Evidence and limits

`source-pin.json` and `source/` pin the inspected files to the reviewed commit. `final-source-check.json` verifies the same hashes after the runs. `reviewed.patch`, `route_controls.py`, the raw receipts, and full stdout and stderr preserve the review data. `results.json` records the exact commands and test runtime sources. The first independent run loads six controls. The startup-payload control is then added and run separately.

The lifecycle return proof uses a fresh Hermes constructor and reports `model_turn_executed: false`. An existing ownership host control also sends an actual HTTP conversation to a scripted local response service. That proves request integration, not private FlashNext inference. No independent route control sends a model request. The primary agent's installed model observations are outside this independent review's evidence.

This review does not qualify installed native model turns, complete removal, reboot, or the release. Concurrent removal changes outside the pinned files are not reviewed here. The review does not change product source, remotes, personal data, memory stores, credentials, staging, or commits.
