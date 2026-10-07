# 2026-10-05: Hermes entry parsing and preserved source bytes

The first import parser split only the literal newline, section-sign, newline delimiter. That preserved bytes but disagreed with Hermes on Windows files. The native source uses `Path.read_text(encoding="utf-8-sig")`, which removes a leading byte order mark and normalizes carriage returns before it splits entries.

A synthetic Windows fixture produces one combined entry with the first parser. Hermes produces two entries. The failing regression retains that difference. The import parser now recognizes the original newline forms, retains exact delimiter bytes and byte offsets, and presents the same normalized entry text as Hermes. Duplicate occurrences retain separate identities. Blank chunks remain accounted for.

The private snapshot retains original bytes before any native mapping. This parsing result does not prove publication, ownership cutover, or reverse migration. Those operations need separate source barriers, target checks, per-item receipts, and acceptance evidence.
