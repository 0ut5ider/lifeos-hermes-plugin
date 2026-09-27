# 2026-09-27: LifeOS child inference bypassed the local gateway

The first Claude Code reference run could answer from the synthetic LifeOS identity, but its prompt processing hook recorded `source: inference-failed` with a 424 ms latency. A direct child invocation returned an API error. The main Claude process was using the local model, so the first assumption was that all LifeOS calls inherited the gateway settings.

Inspection of `LIFEOS/TOOLS/Inference.ts` overturned that assumption. Before launching a child `claude` process, it deletes `ANTHROPIC_API_KEY`, `ANTHROPIC_AUTH_TOKEN`, and `ANTHROPIC_BASE_URL`. This is intentional for its Claude subscription path. It is incompatible with a local-only model unless another layer restores the routing. A user-specific outbound firewall prevented an unintended external request during the experiment.

A `PATH` adapter restored the private gateway settings and translated the child model and effort flags. A direct inference then returned `READY`. In an interactive session, the prompt processing record changed to `source: inference` with a 9,559 ms latency. This result validates the local child path, but it does not validate the intended differences between LifeOS model tiers.
