Date: 2026-10-13
Role: Independent pull request reviewer
Question: Does PR18 provide safe owner-driven installation and complete-package updates through the Hermes dashboard?
Model: gpt-6.1-sol, high reasoning effort

Reviewed head: 3ade1125b5b7db0339d5b214cb2df05b31d45150
Base: origin/main at 958d122a491ddead7c19a5f215494f0422c4b5d6
PR: https://github.com/0ut5ider/lifeos-hermes-plugin/pull/18

## Result

The review has one PR-introduced medium-priority defect. A separate pre-existing high-priority lifecycle gap blocks the requested stock-install-to-update acceptance. The review is not clear for qualification.

## Findings

### P2: A preparation interruption before the worker receipt permanently disables the new UI controls

Location: optional/lifeos_release_manager/release_preparation.py:67-82; optional/lifeos_release_manager/cli.py:153-163; optional/lifeos_release_manager/dashboard/dist/index.js:98-100.

queue() publishes state=preparing and preparation.json before it starts the child and publishes preparation-worker.json. A dashboard process termination between these steps leaves durable preparation state without a worker receipt. preparation_status() only checks process liveness when that receipt exists. It therefore reports preparing indefinitely for this abandoned operation. The UI disables Install LifeOS and both update buttons whenever any operation remains preparing. Refreshing the page or starting the dashboard again does not remove this state.

The same receipt gap can occur after the child starts if the parent dies before it records the identity. A subsequently terminated child then leaves the same state. The profile lock releases on process exit, but status does not consult that lock for missing receipts.

Evidence: interrupted-before-launch.json constructs the exact durable file prefix published before Popen. Two actual status() calls return preparing without a worker receipt. Source inspection establishes that no later path reclassifies this state. The existing interrupted-process tests only cover an already published worker receipt.

Impact: active programs remain intact, but the user cannot retry using the newly requested buttons. A command-line preparation can still proceed, which does not restore the promised self-service UI.

Required correction: give missing-worker launch states a recoverable lifecycle. Distinguish an active launch from an abandoned operation using a held preparation lease and a durable worker identity or launch state. Add controls for interruptions before spawn and between spawn and identity publication. Do not let a status read classify a currently launching process as abandoned.

### P1 acceptance blocker, pre-existing: Fresh installation does not create the service bindings required by its first update

Location: optional/lifeos_release_manager/release_plan.py:48-52 and 65-67; lifeos_hook_bridge/profile_services.py:20-21 and 153-164.

The fresh branch records services=None. The installation plan publishes programs, configuration, launchers, and the integration receipt. NativeInitialization publishes the native and user trees. Neither path provisions systemd unit definitions. The actual pinned native LIFEOS/HERMES/Mount.ts configures prompts, skills, plugin selection, policy, and the environment; it does not provision systemd services.

Every later update unconditionally constructs ProfileServices and calls preview(). This requires all three configured services to be loaded: hermes-gateway.service, hermes-dashboard.service, and com.lifeos.pulse.service. It also requires the expected working directories, reviewed unit properties, and account-owned launcher paths. The parent reports actual stock-guest metadata with a native dashboard unit but no gateway or Pulse unit. Under that measured setup, the next update refuses during preparation. A default stock dashboard definition can also fail the required working-directory binding.

This is not introduced by PR18. baseline-release-plan.py, baseline-release-initialization.py, and baseline-profile-services.py preserve the origin/main implementations. service-lifecycle-pr-diff.txt is empty. It is nevertheless inside the authorized install-and-update acceptance goal and must not be hidden by operator-created service prerequisites between the two user actions.

Evidence limits: I verified the mandatory source paths and the absence of service provisioning in the pinned mount. I did not access or mutate the guest. The guest unit absence is the primary agent's measured result. I did not execute a successful fresh installation followed by an update during this review.

Required correction: resolve service lifecycle ownership for a stock installation. Either provision and recover the required managed service definitions as part of the reviewed package installation, or support the actual verified stock deployment mode when checking updates. Preserve writer-drain and owner-governance guarantees. Verify installation followed directly by an update on the same stock guest, without an intervening operator setup step.

## Checks that pass

I read the coding-rules skill and its JavaScript reference. I reviewed the complete PR diff and relevant unchanged admission, operation, initialization, service, and catalog paths.

The selected Python component command passes 27 tests in 4.504 seconds. It checks exact source validation, isolated Python bytecode refusal, bounded selection parsing, actual file locks, recovery refusal, command version handling, flow-YAML preservation, native dashboard sessions, current owner revocation, foreign origins, and malformed bodies. The run uses -B and ResourceWarning as an error. There are no skipped tests or failures. Unittest writes its expected test report to python.stderr; python.stdout is empty.

The Node command passes all 3 tests. node.stderr is empty. These are SDK rendering/request contract controls with a synthetic SDK. They are not browser acceptance or end-to-end evidence.

The new preparation endpoint rejects client-selected profiles, accounts, shell commands, unrecognized fields, malformed versions, invalid names, query parameters, and oversized bodies. The authenticated owner dependency still uses current memory owner configuration when that configuration exists. The route queues work in a threadpool. Preparation launches a private detached child with stdin disconnected, a retained actual flock descriptor, and a waiter thread. The final apply remains separate from preparation and uses the fixed reviewed request and plan.

Both Update LifeOS and Update plugin intentionally select the complete qualified integration. I did not report their common behavior as a defect.

The source import fix addresses isolated Python ignoring PYTHONDONTWRITEBYTECODE by setting sys.dont_write_bytecode before qualified bridge imports. Its actual isolated-interpreter regression passes. The flow-style YAML correction preserves parsed values in the covered paths and prepares block headers for the native mount. Its regression passes.

## Verification limits

I did not claim browser acceptance, fresh installation acceptance, conversational update acceptance, prerelease publication, certificate qualification, or daily deployment. I did not repair the synthetic recovery-required trial. I did not change source, commit, push, publish, or mutate a guest. The stable 0.4.1 release and daily 0.3.1 installation remain outside this review.

## Raw data

- pr18.diff: complete reviewed diff.
- python.stdout and python.stderr: selected 27-test component run.
- node.stdout and node.stderr: three UI contract controls.
- interrupted_before_launch_probe.py: repeatable temporary-profile probe.
- interrupted-before-launch.json: actual status calls for the durable launch-interruption state.
- baseline-release-plan.py, baseline-release-initialization.py, baseline-profile-services.py: relevant origin/main source.
- service-lifecycle-pr-diff.txt: empty diff establishing that the service gap predates PR18.
