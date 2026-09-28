# Native UserPromptSubmit effects on isolated .212

On 2026-09-28, I exercised four installed LifeOS prompt handlers through the Hermes bridge. Each run used a disposable home or LifeOS root. No model call or real GitHub request was made.

| Handler | Observed effect |
| --- | --- |
| PromptProcessing | `/Research` under the Discord channel wrote `Research Skill Run` to `session-names.json`. A normal synthetic first prompt also reached the configured local model through the child launcher and wrote an inferred session name. The live probe took 5.99 seconds; its telemetry reported `source: inference` and 3,605 ms of inference latency. A repeatable model-backed test passed. |
| DriftReminder | A short prompt received `max 15 prose lines`; a detailed prompt received `depth requested, line cap lifted`. Its state counted two turns. |
| ReminderRouter | An explicit reminder with no `work_repo.json` made no `gh` call and wrote no seen state. A temporary recent private-repository attestation routed the original prompt to a fake `gh issue create` and wrote seen state. |
| VersionDrift | An untagged temporary home returned no context. With `GIT_DIR` pointing at the test host's existing tagged Hermes checkout and `GIT_WORK_TREE` at a disposable directory, it reported 331 changed core files against `v2026.9.24`, wrote a nag record, and stayed silent on the next prompt. The tagged checkout was read only. |
| AlgorithmNudge | A `go deep` prompt returned the depth directive advisory and recorded its cooldown. The immediate repeat was silent. A fresh temporary `USE WHEN` index made a matching prompt recommend `memory-debugging` and recorded its route cooldown. |
| ModelRungGuard | A synthetic `fable` settings pin and `claude-sonnet` bridge transcript produced a two-rung warning and an `off-pin` observability row. No Claude model was called. |

The deployed `.212` LifeOS tree is not a Git checkout. The fresh LifeOS source checkout has no semantic-version tags, so VersionDrift's active branch cannot fire in that installation. The tagged-repository probe verifies hook dispatch and output handling, not a complete LifeOS versioning workflow. PromptProcessing used the `.212` local model; its name quality and distinct Claude tier behavior were not evaluated. ReminderRouter's configured path used a fake `gh` executable, so the probe cannot establish real GitHub delivery. A synthetic tier name tests ModelRungGuard's warning logic but does not give the local model a Claude rung. All 140 plugin tests passed on `.212` with Bun and the installed hook paths configured.
