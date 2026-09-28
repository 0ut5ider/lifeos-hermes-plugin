# Asynchronous hook timeout probe

Date: 2026-09-28. Source inspection showed that local Hermes async hook spools do not copy the configured timeout, while remote async spools do. That suggested a parity bug. We tested it before changing code.

Claude Code 2.1.272 ran a disposable asynchronous UserPromptSubmit hook configured with `timeout: 1`. The hook wrote a start marker, slept three seconds, and wrote a finish marker. Four seconds after the reference turn returned, both markers existed. The [native output](../docs/agents/2026-09-28-native-contract-probe/async-timeout-reference.jsonl) records the result. The same hook through the Hermes bridge on `.212` also produced both markers after four seconds; its [bridge output](../docs/agents/2026-09-28-native-contract-probe/async-timeout-hermes.jsonl) records that result.

For this pinned command-hook form, enforcing a one-second local timeout would diverge from the observed native behavior. No code change was made. Different timeout values, HTTP hooks, remote backends, and hook versions remain unmeasured. The probe created disposable files and removed them after observation.
