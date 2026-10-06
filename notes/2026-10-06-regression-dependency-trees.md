# A prepared source fixture needs twelve dependency trees

2026-10-06, Cerebo. The selected live hook checks pass on installed development
profiles. The broad local regression fixture starts from clean patched source.
Its first native memory operation rejects a write because the source cannot
import `yaml`. Attaching the shared runtime package resolves that import.

The broader tests then expose two more distinct failures. PULSE cannot import
`smol-toml`, and MemoryGraph cannot import `graphology`. The graph failure also
reproduces in one isolated test. These packages live in separate native package
trees. Preparing patches and populating the root runtime package does not create
the complete installed dependency environment. I missed those separate trees in
the initial runner setup.

The release catalog contains twelve package trees. The corrected fixture runs
the actual native dependency wrapper with frozen locks for all twelve. It checks
Bun 1.3.14, source package hashes, final lock hashes, and every declared direct
package. All twelve installs succeed. The isolated graph test now passes with
unchanged product code. The complete regression inventory is rerunning against
that fixture. Its result is still pending at capture time.

Keep source admission and runtime preparation explicit in future comparisons.
Use the verified installer candidate for fresh-store tests. Use a complete
catalog dependency installation for native runtime tests. Retain setup failures
so their results do not become product regression claims.
