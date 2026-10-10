# Retirement tests need a current-source case

Date: 2026-10-08.

A native Finance retirement test first excluded every fixture source. The test expected one unrelated statement to remain visible. Nine other Finance tests passed.

The existing retained-source policy explains the result. An unreviewed source whose timestamp predates the latest applicable retirement is excluded before claim matching. A test that checks only a missing retired string can pass through that source-age fence. It does not establish correct decoding of escaped JSON or YAML claims.

The corrected test checks both branches. Old unreviewed sources stay excluded. The test then refreshes source timestamps while preserving their bytes. Decoded retired vendor and statement claims remain excluded. An unrelated current statement remains visible. The complete 14-case focused gate passes.

This result does not justify relaxing the source-age fence. The additional Finance and Health source classes still need source-review coverage before installed ownership acceptance.
