# Removal preparation and contained dependency links

Date: 2026-10-15.

The actual owner browser preparation979933947547464185a71a935d7324a2 on CT110 reaches stock runtime and recovery source creation. It creates an empty generated directory, then refuses before it writes a removal plan. No active software changes. Both current built-in memory digests remain unchanged.

The native inventory accepts verified contained links in dependency trees. The following software-plan input loop fingerprints those same roots with links disabled. A read-only call on the actual `LIFEOS/PULSE/Observability/node_modules` tree reproduces `ProgramConflict` with the regular-owner-artifact refusal. The synthetic combined software plan reproduces the same call site. The inventory and publisher already use the contained dependency link rules.

The correction applies `allow_links=True` only when the selected path is in the native dependency map. Original native before-image identities still override current measurements. ProgramTransaction refuses edits since inventory. All other program fingerprints keep their existing link rules. Five focused controls pass cleanly, including actual software removal and restoration, an escaping dependency link, and a later dependency edit. The first corrected run exposes a missing launcher parent in the test fixture. Creating that fixture directory produces the clean repeat; the failed run remains recorded.

This is component and diagnostic evidence. A new committed checkpoint still needs the normal installed browser workflow and final package qualification. The daily server is unchanged.
