# Contributing

Start with the [codebase map](docs/codebase.md) to find the implementation and tests for your task. The [documentation index](docs/README.md) distinguishes active guides from dated evidence. Read [TODO.md](TODO.md) before starting unfinished product work.

## Set up an isolated workspace

1. Clone the repository and create a branch for the change.
2. Use a Python environment with the supported Hermes and plugin dependencies.
3. Install Node.js for the dependency-free dashboard component tests.
4. Prepare the pinned upstream sources when your tests need native Hermes or LifeOS code.
5. Use a disposable account or guest for service, installation, or recovery tests.

There is no root `pyproject.toml`, `requirements.txt`, or npm build project. The runtime Python dependency pins are in [`lifeos_hook_bridge/plugin.yaml`](lifeos_hook_bridge/plugin.yaml). A qualified package includes its frozen Python closure. Prefer that environment for package qualification. Native code also needs the Bun version and source fixtures named by its gate.

The supported source inputs are declared in [`install_source.py`](lifeos_hook_bridge/install_source.py) and [`prepare_sources.py`](scripts/prepare_sources.py). The [source preparation guide](docs/clean-install.md) explains their output. Do not use a daily profile, production bot, or personal store as an unplanned test fixture.

## Make a bounded change

Read the existing callers and tests before editing. Keep source, patch copies, declarations, and relevant guides consistent. Add regression tests for behavior changes. Characterize an uncovered path before refactoring it. Use real APIs and processes for installed acceptance. Component fixtures establish their own narrower contracts.

The dashboard `dist/index.js` and `dist/style.css` files are the tracked editable assets. There is no separate plugin-local TypeScript, JSX, or npm build tree. The Hermes host supplies React and the plugin SDK. Both manifests must name their stylesheet. Scope plugin CSS under `.lifeos-setup` so it does not style the host dashboard.

Do not edit historical receipts to match a new result. Add a new dated record and link the old result when it explains the change. Keep prompts, raw model output, credentials, personal memory, private exports, and backup contents outside Git.

## Focused checks

Run commands from the repository root. Start with the smallest meaningful suite for the edited path:

```bash
python -m unittest discover -s tests -p 'test_model_tiers.py' -v
node --test tests/*.cjs
node --check lifeos_hook_bridge/dashboard/dist/index.js
node --check optional/lifeos_release_manager/dashboard/dist/index.js
```

Replace the Python test pattern with the relevant existing file. Examples include `test_bridge.py`, `test_memory_policy.py`, `test_memory_runtime.py`, `test_release_preparation.py`, and `test_release_services.py`. The [codebase map](docs/codebase.md#tests-and-verification) links these test families to their implementations.

Tests can require prepared source paths, Bun, a systemd user manager, process inspection, native services, SSH or container fixtures, or an explicitly configured model endpoint. Check each selected suite's environment variables and skip conditions. A broad `unittest discover` run without those prerequisites does not establish complete qualification. Preserve failures and skips in the report.

For native memory/backend tests, the common source variables are `LIFEOS_HERMES_SOURCE` and `LIFEOS_MEMORY_SOURCE`; the [preparation guide](docs/clean-install.md#use-prepared-sources-in-tests) gives their path shapes. Other suites use different explicit variables. Do not infer that two variables enable every test.

When checking the completed branch, run both working-tree and committed-range whitespace checks:

```bash
git diff --check
git diff --check origin/main...HEAD
```

Component tests, native tests, installed acceptance, and exact-package qualification are separate evidence. Report which layer ran. Do not describe mocked SDK tests as a successful installation or Discord round trip.

## Patch changes

The declared patch order is part of the supported combination. Edit the affected upstream fixture, regenerate the relevant patch, and keep `patches/` and `lifeos_hook_bridge/patches/` synchronized. Re-prepare from the pinned bases and run affected behavior tests. [Patch ownership](docs/patch-footprint.md) explains the groups and regeneration command.

The documentation audit finds one existing mismatch between the two lifecycle patch copies. The [source preparation guide](docs/clean-install.md) records its effect. Resolve the [tracked copy-equivalence follow-up](TODO.md#documentation-audit-follow-ups) before using that development helper as a qualified managed-source substitute.

A patch that applies cleanly can still change behavior. Record upstream replacements explicitly before removing a patch from either declared list. Do not reintroduce the retained, inactive protected-instruction approval patch into the active Hermes sequence.

## Release changes

A version bump identifies a complete integration release. Keep `VERSION`, both plugin YAML versions, and both dashboard manifest versions consistent. [`release_version.py`](lifeos_hook_bridge/release_version.py) verifies declarations and installed identity.

The builder requires committed tracked source and these inputs:

```bash
python scripts/build_managed_release.py \
  --output /path/to/private-build-output \
  --hermes-source /path/to/hermes-agent \
  --lifeos-source /path/to/LifeOS \
  --python-closure /path/to/reviewed-frozen-python-closure
```

The Python closure must contain the reviewed `pyproject.toml`, `uv.lock`, and `plugin-deps/`. A build creates a candidate, not a qualification certificate. The package selects committed paths, including the daily deployment profile and a dated morning-delivery operator. Check [`build_managed_release.py`](scripts/build_managed_release.py) before changing or moving those inputs.

Qualify the exact archive after review. Check its file map before and after tests. Record environment limits and inherited checks. Publish immutable assets only after the required gates. Update development before daily, then add deployment evidence as a new receipt. The [update policy](docs/update-policy.md#qualify-a-new-upstream-combination) gives the sequence; the [0.7.2 record](docs/verification/2026-10-16-release-0.7.2/README.md) is a completed example.

Documentation-only changes do not require a version bump, package rebuild, or server deployment. They must still preserve links, source references, and the meaning of prior evidence.

## Review handoff

Describe the concrete behavior or documentation problem, the resulting change, the checks run, and remaining limits. Link a dated verification record when the evidence is too large for the review description. Keep raw artifacts outside routine reader paths and identify synthetic fixtures clearly.

Before publishing documentation, check that examples use placeholders for account-specific paths and destinations. Follow relative links from the README and contributor guide. Keep task instructions in their canonical guide, and link historical decisions instead of repeating their checkpoint prose.
