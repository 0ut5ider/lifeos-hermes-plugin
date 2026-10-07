# Actual approval lifecycle controls

Date: 2026-10-06. Target: isolated development accounts on `192.168.8.252`.

Three actual Hermes CLI controls pass. The interactive rejection control selects Deny in the real approval panel. The interruption control sends Ctrl+C while that panel waits. The unattended control runs the actual one-shot CLI. Each control leaves the protected `CLAUDE.md` target absent and records one SessionEnd event. Rejection and unattended refusal each record one Stop event. Interruption records no completed Stop event.

The model uses private FlashNext. Five actual requests have successful responses. `wire-proof.json` retains their request and response hashes. The full request bodies remain private on the development server. The earlier approved interactive write in `../evaluation-branches` supplies the complementary allow control. These three controls measure host approval behavior and do not claim a paired native CLI comparison.

The terminal logs and fixture event rows retain the actual outcomes. The runner source and source identity manifest bind the programs used for the controls. Profile configuration, credentials, private request bodies, and caches are excluded. Earlier failed assertions remain in the development cache; the final control uses the measured refusal text.
