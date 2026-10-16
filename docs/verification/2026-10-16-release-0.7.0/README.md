# LifeOS 0.7.0 qualification and promotion

Status: qualification in progress. Development `.252` and daily `.253` still select qualified 0.6.0.

The program commit is `30b383f10fbe76ece98295f53f83322e8d3de880`. The complete archive contains 288,186,773 bytes. Its SHA-256 is `873c0519424bfd4bf920f1ca0aef0c418ad7dc3a222fbe9a8f0a25343ac7629a`.

The [package comparison](package-verification.json) verifies both prepared native trees, their 10 Hermes and 25 LifeOS patches, the frozen Python closure, and the stock Hermes program files against the immutable qualified 0.6.0 archive. The reused local cache contains a generated `.bytecode-fingerprint`; it does not establish native equivalence. The immutable archive comparison passes.

All 36 UI tests pass. The [native check](native-sealed-30b383f1.json) passes all 716 tests in 38 files against this exact archive. The live SSH fixture uses only the owned qualification guest at `.214`. Integration and installed acceptance remain pending. HTTP client acceptance and the three product review rounds remain in the [source verification record](../2026-10-16-http-memory/README.md).

The owned disposable guest is CT110, cloned from the retained stock Hermes snapshot. Production receives the complete package after qualification. No personal data import, reset, provider return, or software removal forms part of this promotion. HTTP access starts disabled on existing servers. Tailscale configuration and external agent enrollment remain separate owner actions.
