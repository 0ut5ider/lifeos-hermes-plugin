# 2026-09-27: LifeOS child inference on the local model

LifeOS child inference requests four Claude model tiers with `--effort high`. The isolated `.212` gateway rejected a direct local-model call with `--effort high` and returned HTTP 400: supported values are `xhigh`, `medium`, and `low`. A direct `--effort xhigh` call to the same local model returned `READY` and reported the local model in `modelUsage`.

The bridge's optional `claude` child launcher now maps LifeOS's Haiku tier to local `low`, Sonnet to `medium`, and Opus/Fable to `xhigh`. It still maps every child to the single configured local model. This preserves a useful effort distinction, but it does not reproduce LifeOS's four distinct model tiers. Unknown model names retain the previous `medium` default.

The mapping is covered by an isolated launcher test, including `--model=value` and `--effort=value` forms. The probe did not run the four native LifeOS inference levels end to end. LifeOS's model verification log will continue to see the executed local model rather than the requested Claude tier.
