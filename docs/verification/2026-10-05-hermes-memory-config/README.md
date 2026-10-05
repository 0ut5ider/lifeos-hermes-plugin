# Hermes lasting stores under configuration failure

Date: 2026-10-05. Role: primary implementation and verification.

Hermes now disables both built-in lasting stores when the current profile configuration cannot be read or parsed. The memory section must be a mapping. Explicit null, collection-valued flags, and nonfinite numeric flags also disable both stores. A missing memory section retains ordinary native defaults. Valid selected flags retain their tested behavior.

The existing raw configuration reader checks the current profile before the merged configuration supplies the memory section. This preserves the distinction between an absent section and an explicit malformed section. FailedConfigRead defaults or last-known-good data cannot grant a lasting-store write. The on-disk store loader also disables both stores if a configured size limit prevents construction.

## Evidence

The corrected original baseline uses actual registry dispatch. It records 16 failures, one pass, and four passing subtests in 7.87 seconds. Malformed sections, parse failures, unreadable config.yaml, malformed flags, and an invalid size limit permit native writes. The first positive controls retain fresh defaults and selected flags.

One initial probe calls MemoryStore.add directly. That storage method does not enforce tool target flags. The public memory handler performs the target check. The recorder and final gate use real registry dispatch. The initial instrumentation remains visible in module-path-output.txt and the handler baseline files.

The first merged-configuration candidate leaves two failures for memory: null. Hermes normalization replaces that section with native defaults before the flag check sees it. The final raw-section check closes both failures without treating a missing section as invalid.

The combined gate passes 21 tests and 38 subtests in 16.58 seconds. It includes the configuration controls, current graph flag controls, source preparation, and footprint contracts. An actual process runs two profiles in A-to-B-to-A order under multiplex scope. Invalid profile A stays disabled while valid profile B retains its flags. The tests capture and assert expected configuration warnings. No live credentials, model calls, or production files enter these controls.

The native Hermes test runner passes 62 tests in three files in 3.3 seconds, with no failures or retries. The recorder retains ten passing controls from both native-process test classes. All 60 assigned Hermes files match the prepared distributed tree. The existing plugin-events group gains tools/memory_tool.py. No patch group or dependency is added.

## Limits

These checks establish configuration admission, store-loader flags, and actual tool dispatch for the tested configurations. They do not establish ownership cutover, draining existing agents, complete startup and required-provider recovery, restricted prompts, full service recovery, or activation. They do not claim every malformed configuration field. A fresh profile with no memory configuration retains enabled native defaults. Ownership setup must explicitly disable both stores in a valid configuration.

No production configuration, ownership, sharing, or service changes. The combined release gate remains open.
