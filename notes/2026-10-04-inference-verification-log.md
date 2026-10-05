# Native inference log escaped publication controls

2026-10-04. Actual adapter inference sends one scripted HTTP request and produces the expected native verification metadata. Its raw logger creates mode 0644 and follows a symbolic link to a foreign file. Both focused regressions fail in 11.87 seconds. The log contains route metadata, not the prompt, but it is still an active writer outside governed publication.

The existing PULSE publisher already checks fixed destinations, current authority, expected bytes, private mode, and journal recovery. Reuse that publication path for the fixed model-verification file. Keep the native metadata fields and best-effort logging contract. A refused log must not erase another file or change the inference result.

Live model acceptance and the complete ownership gate remain separate. The failure record is in docs/verification/2026-10-04-memory-inference-log/before-output.txt.
