# Disposable LifeOS update reference

Date: 2026-09-29. Target: `lifeos-plugin-install-probe` on `.212`.

The installed `.claude` tree uses 1.8 GB. A complete `cp -a --reflink=auto` copy took 5.37 seconds on the test filesystem and used 21,116 KB peak process memory. This makes a private staged tree practical for the test account, although an updater must check free space and handle filesystems without reflinks.

The pinned LifeOS candidate installed into an isolated `HOME` in 14.3 seconds using the six native fresh-install tools. The reference registered 74 hooks. Its deployed system paths included 1,801 files whose bytes matched the source payload, one transformed `bun.lock`, and six generated `bun.lock` files, after excluding dependency directories. The existing account's synthetic USER and MEMORY file hashes stayed at `d9912feeda679977785d364d4e115c7f1e6dbc27d3a96bd4dc5142e01ddb787d` and `f6063f6ca5ee718d1372828e04af9c8156e3ef4933fc86946d4dd6991e747a62`.

The reference installed fewer source files than the payload contains. An update must take its desired file set from a fresh reference installation of the selected candidate. It must not copy every source path or rerun additive installation tools over a populated account. The reference install remains in the disposable account's workspace for the transaction rehearsal.

A read-only plan against the installed tree found 1,825 desired source-backed system files, zero additions, zero replacements, and zero removals for the same candidate. The first version of the planner incorrectly proposed removing five tracked `bun.lock` files. The baseline contained those locks, while the planner had excluded every lock. After separating generated locks from source-matching locks, the live plan kept all 11 lockfiles in the dependency inventory. A staged tree copied from the install then accepted all 13 package roots from the reference in 8.68 seconds. The native `Doctor.ts --hooks` check on that staged tree reported that every registered interpreter resolves.
