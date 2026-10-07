# Fresh store page controls

Date: 2026-10-05. The LifeOS page has a **Fresh LifeOS store** section. It uses the [detached preparation routes](../2026-10-05-fresh-store-worker/README.md). Production on `.212` stays unchanged.

The section:

- asks for your name and the assistant name and starts a detached preparation;
- lists every prepared store with its names and state: ready for review with its active fact count, preparing, interrupted, failed with the reason, or unreadable;
- offers removal for each store except a running one;
- disables the start control while any installation operation runs;
- states that the current installation stays selected and that preparation does not switch memory.

The four new interface tests fail before the implementation ([before.txt](before.txt)). The final interface gate passes 18 tests across the new controls, the memory panel, and the settings page ([after.txt](after.txt)).

The tests run the shipped bundle with a recording SDK. No browser check has run yet, and the page has no refresh while a preparation runs; the owner reloads the page. Store selection, activation, and return are not part of this section.
