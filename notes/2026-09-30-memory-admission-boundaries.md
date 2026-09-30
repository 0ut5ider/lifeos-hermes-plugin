# Memory admission across workers and child calls

Date: 2026-09-30. These observations use synthetic data in disposable local profiles.

Direct runtime tests passed, but the actual Hermes prompt dispatcher exposed two different caller contexts. Its bounded worker copies context variables. Changes inside that worker do not reach the caller. Gateway calls recover admission from durable state and current host metadata. Terminal calls need the host's platform argument because the command-line interface does not set gateway platform metadata. The added terminal regression uses the actual dispatcher and verifies model admission and a provider tool in the caller.

A real localhost gateway test then exposed the raw child route. The local HTTP adapter sent a synthetic private marker to an unapproved endpoint. The adapter now checks the actual endpoint, model, provider identity, and API mode before the request. A separate approved child route can differ from the parent route. It needs an explicit destination grant.

The closure reviewer found that disabling ownership could remove the inherited context marker during environment construction. The next child call treated the installation as inactive and sent the retained marker. Admission now refuses previously recorded conversations after ownership changes. Child environments also carry their conversation identifier. This identifier retains the invalidation check when the detailed context is absent. The unchanged review probe must now stop at admission; the additional regression verifies refusal of both disabled and removed configuration.

The sharing review found an unrelated-key deletion when two SSH entries used the same comment. Revocation now checks the stored credential fingerprint, managed entry form, and client comment. The real SSH test verifies an open MCP connection loses access on its next request. It also verifies a later login fails, private preferences stay excluded, and shell commands fail.

Two fixture traps affected the investigation. OpenSSH StrictModes refuses an authorized-keys path below world-writable `/tmp`. The SSH fixture now uses an owner directory below `~/.cache`. Hermes package-manager builds with an explicit `--requirement` select the requirements lane and ignore project groups. The combined test environment uses the source lane with the `dev` group and no explicit requirement override.

These results do not establish complete native proposal, restricted prompt, lifecycle, or activation coverage. No live memory owner, server key, or `.211` or `.213` installation changed.
