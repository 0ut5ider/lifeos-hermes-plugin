# Memory policy before configuration normalization

2026-10-05, staged LifeOS plugin with the pinned Hermes source. An explicit memory: null section reaches the lasting-store flag reader as a valid default mapping. Checking only the merged configuration leaves both built-in stores enabled. Two actual registry-dispatch controls reproduce writes to MEMORY.md and USER.md after the first candidate fix.

The existing raw configuration reader preserves the distinction. The final reader validates that section before it uses the merged configuration. Missing sections still retain native defaults. Failed reads, explicit null sections, malformed flags, and store-construction failures disable the stores. The combined gate passes 21 tests and 38 subtests. The native test runner passes 62 tests.

The probe also exposes a testing trap: MemoryStore.add is a storage primitive, and the public memory handler enforces target flags. A probe of the primitive can report a write even when the public handler correctly refuses it. The final controls use actual registry dispatch and retain the initial instrumentation. These results do not establish complete ownership activation.
