# Memory publication requires a final authority check

The first revocation experiment passed some explicit writer tests. Those tests revoked access during publication-path planning, before the existing check at the start of the write callback. They did not measure the later validation and source-read window.

Moving revocation into that window produced 13 failures in 14 tests. Native hot writes, archive writes, proposal decisions, explicit corrections, and forgetting could change persistent state. An explicit service could then return an unavailable result because its final response check noticed the revocation. Checking the response alone concealed the completed publication.

The regression runs actual Bun validation, routing, and native writes in isolated stores. Observers change the configuration after a real read or validation and record subsequent native actions. Tests inspect the authoritative files and record references afterward. The fix passes the caller check through curation, archive publication, and proposal decisions, then checks immediately before the native writer or registry mutation. All 14 focused tests pass. This does not make external permission changes atomic with a remote Discord send, which requires its own delivery check.
