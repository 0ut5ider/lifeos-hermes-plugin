# Generic Hermes changes proposed by the LifeOS bridge

Reviewed on 2026-09-28 against the seven patches in `patches/hermes-*.patch`, the current plugin boundary review, and open Hermes issues and pull requests. This is a proposal, not a claim that current Hermes `main` includes these behaviors. Recheck upstream code and issue state before opening each pull request.

Hermes's [contribution guide](https://github.com/NousResearch/hermes-agent/blob/main/CONTRIBUTING.md) asks for focused pull requests with tests and manual verification. Its [plugin guide](https://hermes-agent.nousresearch.com/docs/developer-guide/plugins/) says integrations with other products belong in standalone plugin repositories. The LifeOS hook runner, payload translation, model tier names, and dashboard therefore stay here. The upstream changes below expose general host capabilities or fix host bugs.

| Existing patch | Generic use beyond LifeOS | Proposed upstream destination |
| --- | --- | --- |
| `hermes-remote-file-staleness.patch` | Prevent a whole-file write from silently replacing a change made after the agent's read on SSH or container backends. | Standalone file-safety fix in Hermes. Preserve backend identity, full-read coverage, and the refusal of an unverifiable write. A pre-write digest is not an atomic compare-and-write guarantee. |
| `hermes-cron-worker-bootstrap.patch` | Start scheduled workers with the dependencies of the Hermes installation that launched them. | Standalone runtime fix in Hermes. Test source and managed environment installs without a plugin. |
| `hermes-hook-controls.patch`, nested `execute_code` changes | Keep session and turn identity on tool calls made inside code execution, including remote RPC paths. | Standalone dispatch-context fix. Test local, SSH, and container children with the same parent session. |
| `hermes-hook-controls.patch`, Stop and final-result changes, plus `hermes-stop-effort.patch` | Let retrieval, policy, verification, and quality plugins inspect a candidate response and continue or fail the turn before delivery. Report the effective model and effort. | Join [issue #101910](https://github.com/NousResearch/hermes-agent/issues/101910), which already proposes a universal `before_final` contract. Coordinate with that work before opening a competing pull request. |
| `hermes-hook-controls.patch`, prompt, approval, and tool-result changes | Reject unsafe prompts before persistence, let policy plugins answer a recoverable approval warning, and append post-tool context after result transformation. | Separate generic plugin contracts with explicit precedence and lifecycle tests. Keep Hermes hardline, user-deny, Tirith, and guardian decisions authoritative. Never let a plugin grant override them. |
| `hermes-delegate-tier-routing.patch` and `hermes-delegate-provider-routing.patch` | Run different children in one batch on independently chosen provider, model, and reasoning effort without mutating global config. | Contribute tests and review to [issue #88891](https://github.com/NousResearch/hermes-agent/issues/88891) and [open PR #112741](https://github.com/NousResearch/hermes-agent/pull/112741). Do not open a duplicate implementation while that PR is active. |
| `hermes-direct-provider-inference.patch` | Let a plugin request one selected provider/model/effort through Hermes credentials and reject an unavailable route without fallback. | Separate strict-route and effective-route contract in Hermes's LLM service. Move the plugin-specific child launcher to this repository once a plugin entry module is proven in a packaged install. |

## Proposed order

1. Rebase and reproduce the file-safety, cron worker, and nested identity failures on current Hermes `main`. Submit each confirmed fix with a focused regression and a manual reproduction. These do not require a new plugin contract.
2. Participate in issue #101910. Add our non-coding Stop-hook case, effective route payload, and the requirement that withheld drafts and synthetic continuation prompts never enter durable history or streaming output. A reached retry cap must produce an explicit incomplete result.
3. Review PR #112741 against our route tests. Require each child to receive the resolved provider, model, effort, and allowed toolsets. An explicit selected route must not silently fall back to a different provider. Remove our two delegation patches only after that contract passes the bridge's real child tests.
4. Propose prompt admission, post-transform context, and command approval as distinct host contracts. Document exact timing and precedence before coding. A native LifeOS denial currently prevents a bridge grant, but Hermes's approval contract does not make it an absolute command veto. Resolve that authority gap before claiming PermissionRequest parity.
5. Propose a strict LLM route API with observable effective provider/model/effort. Keep credentials in Hermes and LifeOS tier names in the plugin. Remove the direct-provider patch only after a packaged plugin proves text, image, error, and no-fallback behavior.

## Acceptance rule for removing a local patch

Upstream acceptance alone does not prove the bridge works on a newer release. For each patch, install a pinned Hermes commit without that patch into the isolated `.212` account, run the relevant Hermes tests and native LifeOS effect tests, then exercise the affected CLI, gateway, SSH, Docker, or Discord route. Record the tested Hermes, LifeOS, and plugin revisions. Do not change production `.211` or `.213` during this migration.

The [plugin boundary review](agents/2026-09-28-plugin-boundary-review/plugin-boundary-review.md) explains why copying Hermes built-in tools or monkeypatching the agent loop into a plugin would preserve the same update risk.
