# Tier effort on the wire

Date: 2026-10-05. Four direct LifeOS child calls run through the candidate Hermes provider route on `.212`. Each call selects one tier. A recording relay forwards each request to private FlashNext. Production profiles stay unchanged.

| Tier | Caller effort argument | Effort on the wire | Response |
| --- | --- | --- | --- |
| Haiku | `medium` | `low` | HTTP 200, `READY` |
| Sonnet | `medium` | `medium` | HTTP 200, `READY` |
| Opus | `medium` | `xhigh` | HTTP 200, `READY` |
| Fable | `medium` | `xhigh` | HTTP 200, `READY` |

Each call starts at the bundled child launcher with `--model <tier> --effort medium`. The launcher resolves the tier through `LIFEOS_MODEL_TIER_MAP` and starts `hermes lifeos-infer` with the selected provider. Each tier sends exactly one `/v1/chat/completions` request. The request body has three keys: `messages`, `model`, and `reasoning_effort`. The tier mapping replaces the caller's effort argument in every case. The reported model usage names the actual private model.

[tier-results.json](tier-results.json) retains the commands, request hashes, wire effort fields, response status, and client output. Run `python3 docs/verification/2026-10-05-tier-route-wire/verify.py` to check the results against Adrian's mapping. [run.py](run.py) is the detached runner. It uses the committed `scripts/paired_response_server.py` and the hermes section of [configuration.json](configuration.json). Full wire bodies remain private outside Git.

This unit covers direct child calls with an explicit tier map. It does not cover the main conversation loop, delegated Agent children, nested inference, tier settings read from the installed plugin configuration, or background jobs. Those routing checks remain open. No product code changes in this unit.
