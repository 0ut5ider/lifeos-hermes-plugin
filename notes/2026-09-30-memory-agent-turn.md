# Verify the receipt through the complete agent turn

Date: 2026-09-30. All identities, prompts, facts, and HTTP responses are synthetic.

The complete Hermes turn makes two model requests to a local endpoint. The first response requests the LifeOS remember tool. The real dispatcher and native backend commit the fact. The second request carries the returned receipt, and the endpoint reports that receipt's status, reference, and writer. A separate read verifies the persisted writer `chat-a:100`, project `lab`, category `project`, and exact content. Neither built-in memory marker reaches either request.

The unknown-author turn stops at prompt admission. It reports `prompt_blocked`, makes zero model calls, and creates no matching fact. Hermes calls this completed handling with `failed=false`. The first test wrongly treated that field as proof of admission failure. The corrected test asserts the block reason, zero calls, and no native effect.

The first fixture also supplied 16,384 tokens and hit the host's 64,000-token minimum. The complete agent fixture now supplies 131,072 tokens. This was a fixture correction, not a host behavior change.

Independent review passes 16 focused tests and finds no material issue in this unit. The primary agent reruns the saved native-writer probe. The model endpoint is deterministic; the test proves integration, not a real model's tool choice or reasoning quality. Native automatic recall is not configured in this fixture. Background review, compression rotation, final delivery, and ownership activation remain separate gates.
