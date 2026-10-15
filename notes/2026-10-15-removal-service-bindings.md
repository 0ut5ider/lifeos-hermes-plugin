# Removal needs both service definitions

Date: 2026-10-15.

The first removal controller treats every service definition like an account-owned program target. Actual systemd fixtures reject that assumption. Fedora inherits `/usr/lib/systemd/user/service.d/10-timeout-abort.conf`, owned by root with mode 0644, for all three fixture services. The existing profile service verifier correctly accepts that protected file. The new controller incorrectly refuses it through a program fingerprint that requires the account UID.

The corrected controller uses the existing trusted service-file reader to bind the original physical path, content digest, owner, and permissions. Inherited files remain present and must keep their exact identity. Removal targets still require regular account-owned files. Three actual service tests pass: remove Pulse and restart Hermes only, refuse a later unit edit before stopping, and refuse an active or enabled Pulse before preparation. This is a component result, not complete removal acceptance.

The read-only check against the fresh managed guest identifies 1,839 native files, 12 dependency trees, and 74 owned hooks. It publishes no changes. User stores remain outside the target map. A standalone recovery path uses the actual Hermes basic authentication provider and the same installation owner grant. It does not derive authority from shell access alone.
