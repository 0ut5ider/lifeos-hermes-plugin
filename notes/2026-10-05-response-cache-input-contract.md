# Response cache input contract

Date: 2026-10-05.

The first paired LastResponseCache controls fail all three cases. Both caches correctly store `READY` for short replies, but Claude Code displays `\n\nREADY` and supplies `READY` in its Stop payload. The fixture incorrectly requires byte equality between the cache and the displayed result. The retained Stop input proves that the hook receives trimmed text. The corrected assertion checks exact cache bytes against the actual Stop message prefix. It separately compares the Stop message and displayed result after surrounding whitespace removal. Raw inputs and outputs stay retained.

The long-output fixture also fails to exercise truncation. A request for 800 repetitions of `ABCD` produces only 370 and 1,266 cached characters. These outputs cannot establish the 2,000-character limit. The revised prompt requests 24 numbered prose paragraphs with three sentences and distinct examples. The actual run must produce more than 2,000 characters before the truncation case can pass. No shorter output counts as evidence.

The focused fixture, assertion, inventory, trace, and relay suite passes 42 tests and six subtests. The second actual paired cache run passes all three pairs and all six clients. Both long Stop messages exceed 2,000 characters, and both caches contain exactly the first 2,000 characters. No product fix follows the first failed comparison because the measured cache contents match the real hook input on both sides.
