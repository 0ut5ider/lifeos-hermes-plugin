# Main, delegated, and nested routes on the wire

Date: 2026-10-06. This unit records the model requests of real Hermes turns in the disposable guest CT `100`. A loopback relay ([run_routes.py](run_routes.py) with the committed `scripts/paired_response_server.py`) forwards each request to private FlashNext and records the request fields. The runner points the profile model route at the relay for the run and restores it afterwards. The four LifeOS tiers use the `custom` FlashNext provider and Adrian's effort mapping: Haiku low, Sonnet medium, Opus xhigh, Fable xhigh. The Hermes main loop uses `agent.reasoning_effort: medium`. Full request bodies stay private in the guest.

## Results

[route-results.json](route-results.json) lists every chat request with its effort, status, message count, tool count, and the first characters of its system prompt.

| Request | Source | Effort on the wire | Status |
| --- | --- | --- | --- |
| Main turn | Hermes main loop with the LifeOS constitution | `medium` (configured) | 200 |
| Prompt analysis | Native `PromptProcessing` hook through the plugin helper route, inference level `medium` (Sonnet tier) | `medium` | 200 |
| Delegated child with `model: "opus"` | `delegate_task` child after the plugin maps the tier alias | `xhigh` | 200 |
| Parent turn after the child | Hermes main loop | `medium` | 200 |
| Session title | Hermes auxiliary title generation | `none` | 500 during the run |

The main loop keeps its configured effort. The delegated child receives the mapped Opus effort, and the parent continues at its own effort. The nested hook inference uses the tier that the native hook requests. All LifeOS requests name the private model `flashnext-w4a16-fp8ple`.

## Title generation failures

During both turns, every Hermes title request returned HTTP 500 (`Internal server error`), three attempts per turn. A first probe showed failures only when the request had both a reasoning effort and the strict JSON schema response format ([title-probe.txt](title-probe.txt) records the later rerun). A rerun of the same probe minutes later returned 200 for every variant, including the exact recorded request. Fifteen further sends of the recorded request, ten alone and five beside a concurrent main-sized request, all returned 200 ([title-repeat.txt](title-repeat.txt)). The field-combination hypothesis is therefore wrong. The cause of the failures during the run is not known. Title generation is a Hermes auxiliary task, not a LifeOS route, and Hermes falls back to its derived title.

## Limits

- One run per scenario. The delegated scenario relies on the model to call `delegate_task` with the requested alias; it did so once.
- Nested inference inside a delegated child does not occur: Hermes runs no session-start or prompt hooks for delegated children, as Claude Code does for subagents.
- Background jobs, scheduled Pulse work, and the gateway messaging path are not covered.
- The relay records the requested effort field. It does not attest to the reasoning depth inside the private server.
